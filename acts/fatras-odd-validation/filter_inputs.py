#!/usr/bin/env python3
"""Apply one transport input selection before either simulator reads the CSVs."""
import argparse, csv, hashlib, json, math
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("source", type=Path)
p.add_argument("output", type=Path)
p.add_argument("--max-r", type=float, default=1202.0)
p.add_argument("--max-z", type=float, default=4002.0)
p.add_argument("--p-min", type=float, default=0.1)
p.add_argument("--pt-min", type=float, default=0.05)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
counts = {}
hashes = {}
for path in sorted(a.source.glob("event*-particles.csv")):
    with path.open() as f:
        reader = csv.DictReader(f)
        names = reader.fieldnames
        rows = list(reader)
    kept = []
    reasons = {}
    for row in rows:
        px, py, pz = (float(row[k]) for k in ("px", "py", "pz"))
        pt = math.hypot(px, py)
        mom = math.hypot(pt, pz)
        pdg = int(row["particle_type"])
        q = float(row["q"])
        reason = "keep"
        if (
            math.hypot(float(row["vx"]), float(row["vy"])) >= a.max_r
            or abs(float(row["vz"])) >= a.max_z
        ):
            reason = "outside_tracker"
        elif abs(pdg) in (12, 14, 16):
            reason = "neutrino"
        elif mom == 0:
            reason = "at_rest"
        elif pdg not in (310, 3122, -3122, 111) and (
            mom < a.p_min or (q != 0 and pt < a.pt_min)
        ):
            reason = "momentum"
        reasons[reason] = reasons.get(reason, 0) + 1
        if reason == "keep":
            kept.append(row)
    dst = a.output / path.name
    with dst.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)
    counts[path.name] = reasons
    hashes[path.name] = hashlib.sha256(dst.read_bytes()).hexdigest()
(a.output / "selection.json").write_text(
    json.dumps(
        {
            "max_r_mm": a.max_r,
            "max_abs_z_mm": a.max_z,
            "p_min_GeV": a.p_min,
            "pt_min_GeV": a.pt_min,
            "counts": counts,
            "sha256": hashes,
        },
        indent=2,
    )
    + "\n"
)
print(
    "Selected",
    sum(x.get("keep", 0) for x in counts.values()),
    "particles in",
    len(counts),
    "events",
)
