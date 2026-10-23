#!/usr/bin/env python3
"""Matched event-level transport comparisons without rerunning Geant4."""

import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--run", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--reference", type=Path, required=True)
a = p.parse_args()
spec = importlib.util.spec_from_file_location(
    "gaps", "/Users/andreas/cern/scripts/acts/fatras-realism/fatras-charged-mesons/secondary-gaps.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
meta = json.loads((a.run / "metadata.json").read_text())
n = meta["events"]
ref = json.loads(a.reference.read_text())
rows = []
for event in range(n):
    row = mod.analyse(a.run, event)
    hit_path = a.run / f"event{event:09d}-hits.csv"
    if not hit_path.exists():
        hit_path = hit_path.with_suffix(".csv.gz")
    h = pd.read_csv(
        hit_path,
        usecols=["particle_id_gen", "geometry_id", "tpx", "tpy", "tpz"],
        dtype={"geometry_id": "uint64"},
    )
    pt = np.hypot(h.tpx, h.tpy)
    mask = (
        np.isin(h.geometry_id.to_numpy() >> np.uint64(56), [16, 17, 18])
        & (pt >= 0.05)
        & (np.hypot(pt, h.tpz) >= 0.1)
    )
    row["primary_hits"] = int(sum(mask & (h.particle_id_gen == 0)))
    rows.append(row)
previous = ref["runs"]["Current Fatras"]["events"][:n]
g4 = ref["runs"]["Geant4"]["events"][:n]


def total(e):
    return sum(v["hits"] for v in e["process"].values())


def stats(x):
    return {
        "mean": float(np.mean(x)),
        "sem": float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else None,
    }


result = {
    "source": str(a.run),
    "metadata": meta,
    "events": rows,
    "summary": {
        "secondary_hits": stats([total(e) for e in rows]),
        "previous_secondary_hits": stats([total(e) for e in previous]),
        "geant4_secondary_hits": stats([total(e) for e in g4]),
        "paired_secondary_gain": stats(
            [total(e) - total(b) for e, b in zip(rows, previous)]
        ),
        "primary_hits": stats([e["primary_hits"] for e in rows]),
        "cpu_s_per_event": meta["sequencer_cpu_seconds"] / n,
        "process": {
            k: {
                "hits": stats([e["process"][k]["hits"] for e in rows]),
                "paired_gain": stats(
                    [
                        e["process"][k]["hits"] - b["process"][k]["hits"]
                        for e, b in zip(rows, previous)
                    ]
                ),
                "particles": stats([e["process"][k]["hit_particles"] for e in rows]),
                "three_sensor_particles": stats(
                    [e["process"][k]["particles_at_least_3_sensors"] for e in rows]
                ),
                "repeats": stats(
                    [e["process"][k]["repeated_sensor_hits"] for e in rows]
                ),
            }
            for k in ["conversion", "decay", "nuclear"]
        },
    },
}
a.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result["summary"], indent=2))
