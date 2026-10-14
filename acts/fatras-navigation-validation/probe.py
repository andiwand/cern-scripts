#!/usr/bin/env python3
"""Generate stable muons and compare deterministic sensor crossings."""

import argparse, csv, json, math
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--runs", type=Path, nargs="*", default=[])
p.add_argument("--output", type=Path)
a = p.parse_args()
if not a.runs:
    a.input.mkdir(parents=True, exist_ok=True)
    rows = []
    for pt in [0.02, 0.05, 0.1, 0.2, 0.5, 1.0]:
        for eta in [0.0, 1.0, 2.0]:
            for j in range(8):
                for radius in [0.0, 40.0, 120.0]:
                    rows.append(
                        [
                            1,
                            0,
                            len(rows) + 1,
                            0,
                            0,
                            13,
                            0,
                            radius,
                            0,
                            0,
                            0,
                            pt * math.cos(j * math.pi / 4),
                            pt * math.sin(j * math.pi / 4),
                            pt * math.sinh(eta),
                            0.105658375,
                            -1,
                        ]
                    )
    with (a.input / "event000000000-particles.csv").open("w") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            "particle_id_pv,particle_id_sv,particle_id_part,particle_id_gen,particle_id_subpart,particle_type,process,vx,vy,vz,vt,px,py,pz,m,q".split(
                ","
            )
        )
        w.writerows(rows)
else:
    import pandas as pd
    import numpy as np

    truth = pd.read_csv(a.input / "event000000000-particles.csv")
    result = {
        "scope": "Stable muon transport without interactions; deterministic navigator comparison, no Geant4 ground truth. Inclusive pixel crossings and unique sensor IDs per particle.",
        "runs": {},
    }
    for run in a.runs:
        h = pd.read_csv(
            run / "event000000000-hits.csv", dtype={"geometry_id": "uint64"}
        )
        h = h[np.isin(h.geometry_id.to_numpy() >> np.uint64(56), [16, 17, 18])]
        events = {}
        for row in truth.itertuples():
            t = h[h.particle_id_part == row.particle_id_part]
            events[str(row.particle_id_part)] = {
                "pt_GeV": math.hypot(row.px, row.py),
                "eta": math.asinh(row.pz / math.hypot(row.px, row.py)),
                "radius_mm": row.vx,
                "hits": len(t),
                "sensors": sorted(int(v) for v in t.geometry_id.unique()),
            }
        result["runs"][run.name] = {
            "particles": events,
            "hits": len(h),
            "unique_particle_sensors": sum(len(v["sensors"]) for v in events.values()),
            "audit": json.loads((run / "navigation-audit.json").read_text()),
        }
    from itertools import combinations

    result["comparisons"] = {}
    for first, second in combinations(result["runs"], 2):
        left = result["runs"][first]["particles"]
        right = result["runs"][second]["particles"]
        changed = [
            k
            for k in left
            if left[k]["hits"] != right[k]["hits"]
            or left[k]["sensors"] != right[k]["sensors"]
        ]
        result["comparisons"][first + " -> " + second] = {
            "changed_particles": len(changed),
            "hit_difference": sum(right[k]["hits"] - left[k]["hits"] for k in left),
            "added_particle_sensors": sum(
                len(set(right[k]["sensors"]) - set(left[k]["sensors"])) for k in left
            ),
            "lost_particle_sensors": sum(
                len(set(left[k]["sensors"]) - set(right[k]["sensors"])) for k in left
            ),
            "changed_particle_ids": changed,
        }
    a.output.write_text(json.dumps(result, indent=2) + "\n")
