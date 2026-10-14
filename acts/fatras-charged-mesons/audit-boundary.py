#!/usr/bin/env python3
"""Verify every recorded Geant4 birth vertex and hit is inside the ID world."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--events", type=int, default=20)
a = p.parse_args()
meta = json.loads((a.input / "metadata.json").read_text())
world = meta["geant4_world"]
assert world["world_solid"] == "G4Tubs"
radius, half_length = world["radius_mm"], world["half_length_mm"]
# CSV float output can round a boundary point outward by fractions of a micron.
tolerance = 0.001
report = {
    "source": str(a.input),
    "radius_mm": radius,
    "half_length_mm": half_length,
    "csv_tolerance_mm": tolerance,
    "events": [],
}
for event in range(a.events):
    row = {"event": event}
    for stem, columns in [
        ("particles_simulated", ["vx", "vy", "vz"]),
        ("hits", ["tx", "ty", "tz"]),
    ]:
        count = outside = 0
        rmax = zmax = 0.0
        path = a.input / f"event{event:09d}-{stem}.csv"
        for chunk in pd.read_csv(path, usecols=columns, chunksize=100000):
            r = np.hypot(chunk[columns[0]], chunk[columns[1]])
            z = np.abs(chunk[columns[2]])
            assert np.isfinite(r).all() and np.isfinite(z).all()
            count += len(chunk)
            outside += int(
                ((r > radius + tolerance) | (z > half_length + tolerance)).sum()
            )
            rmax = max(rmax, float(r.max()))
            zmax = max(zmax, float(z.max()))
        row[stem] = {
            "count": count,
            "outside": outside,
            "max_r_mm": rmax,
            "max_abs_z_mm": zmax,
        }
    report["events"].append(row)
a.output.write_text(json.dumps(report, indent=2) + "\n")
assert all(
    r[s]["outside"] == 0
    for r in report["events"]
    for s in ["particles_simulated", "hits"]
), "Outside-ID records found"
print(
    "All recorded birth vertices and hits are within the ID world in",
    a.events,
    "events.",
)
