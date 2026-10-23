#!/usr/bin/env python3
"""Separate the accepted-track deficit from inclusive soft pixel occupancy."""

import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--fatras", type=Path, required=True)
p.add_argument("--geant4", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--events", type=int, default=20)
p.add_argument("--trials", type=Path, nargs="*", default=[])
p.add_argument("--reference-processes", action="store_true")
a = p.parse_args()
result = {
    "scope": "Secondary pixel hits, volumes 16–18; no momentum cuts unless stated. A hit is one recorded sensitive crossing, not a reconstructed cluster.",
    "runs": {},
}
BAR = ["particle_id_" + k for k in ["pv", "sv", "part", "gen", "subpart"]]
for label, folder in [("Current Fatras", a.fatras), ("Geant4", a.geant4)] + [
    (v.name, v) for v in a.trials
]:
    rows = []
    n = (
        a.events
        if label in ["Current Fatras", "Geant4"]
        else json.loads((folder / "metadata.json").read_text())["events"]
    )
    for event in range(n):
        hit_path = folder / f"event{event:09d}-hits.csv"
        if not hit_path.exists():
            hit_path = hit_path.with_suffix(".csv.gz")
        h = pd.read_csv(
            hit_path,
            usecols=BAR + ["geometry_id", "tpx", "tpy", "tpz"],
            dtype={"geometry_id": "uint64"},
        )
        h = h[
            (h.particle_id_gen > 0)
            & np.isin(h.geometry_id.to_numpy() >> np.uint64(56), [16, 17, 18])
        ]
        pt = np.hypot(h.tpx, h.tpy)
        mom = np.hypot(pt, h.tpz)
        rows.append(
            {
                "event": event,
                "all": len(h),
                "accepted": int(((pt >= 0.05) & (mom >= 0.1)).sum()),
                "below_pt_only": int(((pt < 0.05) & (mom >= 0.1)).sum()),
                "below_p_only": int(((pt >= 0.05) & (mom < 0.1)).sum()),
                "below_both": int(((pt < 0.05) & (mom < 0.1)).sum()),
                "pt_bins": np.histogram(
                    pt, bins=[0, 0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1, np.inf]
                )[0].tolist(),
            }
        )
        if label == "Geant4" and a.reference_processes:
            truth = folder / f"event{event:09d}-particles_simulated.csv"
            if not truth.exists():
                truth = truth.with_suffix(".csv.gz")
            d = pd.read_csv(truth, usecols=BAR + ["process", "particle_type"])
            ids = pd.MultiIndex.from_frame(d[BAR])
            assert ids.is_unique
            where = ids.get_indexer(pd.MultiIndex.from_frame(h[BAR]))
            assert np.all(where >= 0)
            soft = (pt < 0.05) | (mom < 0.1)
            rows[-1]["soft_process"] = {
                str(k): int(v)
                for k, v in d.iloc[where[soft]].process.value_counts().items()
            }
            rows[-1]["soft_pdg"] = {
                str(k): int(v)
                for k, v in d.iloc[where[soft]].particle_type.value_counts().items()
            }
        print(label, event, flush=True)
    result["runs"][label] = rows
result["summary"] = {}
for key in ["all", "accepted", "below_pt_only", "below_p_only", "below_both"]:
    delta = np.array(
        [
            g[key] - f[key]
            for f, g in zip(result["runs"]["Current Fatras"], result["runs"]["Geant4"])
        ]
    )
    result["summary"][key] = {
        "fatras_mean": float(
            np.mean([e[key] for e in result["runs"]["Current Fatras"]])
        ),
        "geant4_mean": float(np.mean([e[key] for e in result["runs"]["Geant4"]])),
        "gap": float(delta.mean()),
        "paired_sem": float(delta.std(ddof=1) / np.sqrt(len(delta))),
    }
a.output.write_text(json.dumps(result, indent=2) + "\n")
