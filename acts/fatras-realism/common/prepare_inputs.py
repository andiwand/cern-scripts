#!/usr/bin/env python3
"""Select generated particles before either simulator reads the CSVs.

Default (inclusive): keep births inside the ID (r < 1202 mm, |z| < 4002 mm);
no momentum, species or at-rest cuts.

--matched: additionally drop neutrinos, particles at rest and particles below
--p-min / charged below --pt-min (GeV); K-short, Lambda and pi0 bypass the
momentum cuts. This is the selection of the matched odd_run.py comparison.

Writes the selected CSVs and selection.json with counts and SHA256 sums.
"""

import argparse, csv, hashlib, json, math
from pathlib import Path

p = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
p.add_argument("source", type=Path, help="Generator output (odd_run.py generate)")
p.add_argument("output", type=Path)
p.add_argument("--max-r", type=float, default=1202.0)
p.add_argument("--max-z", type=float, default=4002.0)
p.add_argument("--matched", action="store_true")
p.add_argument("--p-min", type=float, default=0.1)
p.add_argument("--pt-min", type=float, default=0.05)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
result = {
    "source": str(a.source),
    "max_r_mm": a.max_r,
    "max_abs_z_mm": a.max_z,
    "p_min_GeV": a.p_min if a.matched else None,
    "pt_min_GeV": a.pt_min if a.matched else None,
    "species_selection": "no neutrinos" if a.matched else None,
    "at_rest_selection": "removed" if a.matched else None,
    "counts": {},
    "sha256": {},
    "source_sha256": {},
}
generator = a.source / "metadata.json"
if generator.exists():
    result["generator_metadata"] = json.loads(generator.read_text())


def reason(row):
    if (
        math.hypot(float(row["vx"]), float(row["vy"])) >= a.max_r
        or abs(float(row["vz"])) >= a.max_z
    ):
        return "outside_tracker"
    if not a.matched:
        return "keep"
    px, py, pz = (float(row[k]) for k in ("px", "py", "pz"))
    pt = math.hypot(px, py)
    mom = math.hypot(pt, pz)
    pdg = int(row["particle_type"])
    if abs(pdg) in (12, 14, 16):
        return "neutrino"
    if mom == 0:
        return "at_rest"
    if pdg not in (310, 3122, -3122, 111) and (
        mom < a.p_min or (float(row["q"]) != 0 and pt < a.pt_min)
    ):
        return "momentum"
    return "keep"


for source in sorted(a.source.glob("event*-particles.csv")):
    with source.open() as f:
        reader = csv.DictReader(f)
        names = reader.fieldnames
        rows = list(reader)
    counts = {}
    kept = []
    for row in rows:
        r = reason(row)
        counts[r] = counts.get(r, 0) + 1
        if r == "keep":
            kept.append(row)
    out = a.output / source.name
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=names, lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
    result["counts"][source.name] = counts
    result["sha256"][source.name] = hashlib.sha256(out.read_bytes()).hexdigest()
    result["source_sha256"][source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
(a.output / "selection.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    "Selected",
    sum(c.get("keep", 0) for c in result["counts"].values()),
    "particles in",
    len(result["counts"]),
    "events",
)
