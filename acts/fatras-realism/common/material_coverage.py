#!/usr/bin/env python3
"""Audit elemental table lookup against the ODD mapped effective materials."""
import argparse, json
import numpy as np
import uproot
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("map", type=Path)
p.add_argument("output", type=Path)
p.add_argument("--table", type=Path, required=True)
a = p.parse_args()
with a.table.open() as stream:
    assert next(stream).strip() == "ACTS_FATRAS_NUCLEAR_V1"
    next(stream)
    channel = next(stream).split()
    target_ar = float(channel[2])
    target_z = float(channel[3])
f = uproot.open(a.map)
rows = []
for key in f.keys(recursive=False, cycle=False):
    if not key.startswith("SurfaceMaterial_"):
        continue
    d = f[key]
    ar = d["A"].values()
    z = d["Z"].values()
    t = d["t"].values()
    l0 = d["l0"].values()
    valid = (t > 0) & (l0 > 0) & np.isfinite(l0)
    # Same relative tolerance as the runtime lookup.
    match = (
        (np.abs(ar - target_ar) <= 1e-3 * np.maximum(np.abs(ar), target_ar))
        & (np.abs(z - target_z) <= 1e-3 * np.maximum(np.abs(z), target_z))
        & valid
    )
    if valid.any():
        rows.append(
            {
                "surface": key,
                "bins": int(valid.sum()),
                "silicon_match_bins": int(match.sum()),
                "Ar_min": float(ar[valid].min()),
                "Ar_max": float(ar[valid].max()),
                "Z_min": float(z[valid].min()),
                "Z_max": float(z[valid].max()),
                "sum_t_over_L0": float((t[valid] / l0[valid]).sum()),
                "matched_sum_t_over_L0": float((t[match] / l0[match]).sum()),
            }
        )
a.output.write_text(
    json.dumps(
        {
            "table": str(a.table),
            "target_Ar": target_ar,
            "target_Z": target_z,
            "note": "Map-bin audit, not track-flux-weighted material coverage; effective Ar/Z only, matching the current silicon table",
            "surfaces": rows,
        },
        indent=2,
    )
    + "\n"
)
print(
    len(rows),
    "surfaces;",
    sum(r["bins"] for r in rows),
    "material bins;",
    sum(r["silicon_match_bins"] for r in rows),
    "match silicon",
)
