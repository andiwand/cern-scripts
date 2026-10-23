#!/usr/bin/env python3
"""Measure reference hit exposure to charged birth cuts along the ancestry."""

import argparse, json, collections
from pathlib import Path
import numpy as np
import pandas as pd

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--events", type=int, default=20)
a = p.parse_args()
BAR = ["particle_id_" + s for s in ["pv", "sv", "part", "gen", "subpart"]]
PARENT = [s.replace("particle_id_", "parent_id_") for s in BAR]
rows = []
for event in range(a.events):
    stem = f"event{event:09d}"
    h = pd.read_csv(
        a.input / (stem + "-hits.csv"),
        usecols=BAR + ["geometry_id", "tpx", "tpy", "tpz"],
        dtype={"geometry_id": "uint64"},
    )
    pt = np.hypot(h.tpx, h.tpy)
    h = h[
        (h.particle_id_gen > 0)
        & np.isin(h.geometry_id.to_numpy() >> np.uint64(56), [16, 17, 18])
        & (pt >= 0.05)
        & (np.hypot(pt, h.tpz) >= 0.1)
    ]
    truth = a.input / (stem + "-particles_simulated.csv")
    truth = truth if truth.exists() else truth.with_suffix(".csv.gz")
    d = pd.read_csv(
        truth,
        usecols=BAR + PARENT + ["particle_type", "process", "px", "py", "pz", "q"],
    )
    ids = pd.MultiIndex.from_frame(d[BAR])
    where = ids.get_indexer(pd.MultiIndex.from_frame(h[BAR]))
    assert np.all(where >= 0)
    birthpt = np.hypot(d.px, d.py).to_numpy()
    birthp = np.hypot(birthpt, d.pz)
    charged = d.q.to_numpy() != 0
    pdg = d.particle_type.to_numpy()
    proc = d.process.to_numpy()
    below = charged & ((birthp < 0.1) | (birthpt < 0.05))
    first = np.full(len(h), -1, dtype=np.int64)
    current = where.copy()
    visited = np.zeros(len(h), dtype=np.int16)
    for depth in range(100):
        live = (current >= 0) & (first < 0)
        if not np.any(live):
            break
        ii = np.flatnonzero(live)
        xx = current[ii]
        hit = below[xx]
        first[ii[hit]] = xx[hit]
        remain = ii[~hit]
        if len(remain):
            new = ids.get_indexer(
                pd.MultiIndex.from_frame(d.iloc[current[remain]][PARENT])
            )
            new[new == current[remain]] = -1
            current[remain] = new
            visited[remain] += 1
    else:
        raise RuntimeError("Ancestry did not terminate")
    row = {
        "event": event,
        "accepted_secondary_hits": len(h),
        "carrier_born_below_cuts": int(np.count_nonzero(below[where])),
        "any_charged_ancestor_born_below_cuts": int(np.count_nonzero(first >= 0)),
        "first_below_cut_pdg": dict(
            collections.Counter(str(x) for x in pdg[first[first >= 0]])
        ),
        "carrier_below_cut_process": dict(
            collections.Counter(str(x) for x in proc[where[below[where]]])
        ),
        "max_walk_depth": int(visited.max()),
    }
    rows.append(row)
    print(
        event,
        row["carrier_born_below_cuts"],
        row["any_charged_ancestor_born_below_cuts"],
        flush=True,
    )
result = {
    "scope": "Matched common-cut secondary pixel hits; first below-cut charged ancestor is nearest the hit carrier. Birth momentum is used, not momentum at a subsequent interaction. Counts are exposure indicators, not recoverable gains. No new Geant4 transport.",
    "input": str(a.input),
    "events": rows,
}
a.output.write_text(json.dumps(result, indent=2) + "\n")
