#!/usr/bin/env python3
"""Keep generated particles inside the ID; impose no momentum/species cuts."""

import argparse, csv, hashlib, json, math
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
result = {
    "source": str(a.source),
    "max_r_mm": 1202.0,
    "max_abs_z_mm": 4002.0,
    "p_min_GeV": None,
    "pt_min_GeV": None,
    "species_selection": None,
    "at_rest_selection": None,
    "counts": {},
    "sha256": {},
    "source_sha256": {},
    "generator_metadata": json.loads((a.source / "metadata.json").read_text()),
    "generator_correction": "The helper at the generator revision uses FixedMultiplicityGenerator(n=200), not Poisson pileup. The generator metadata p/pt fields are unused in generate mode.",
}
for source in sorted(a.source.glob("event*-particles.csv")):
    with source.open() as f:
        reader = csv.DictReader(f)
        names = reader.fieldnames
        rows = list(reader)
    kept = [
        v
        for v in rows
        if math.hypot(float(v["vx"]), float(v["vy"])) < 1202
        and abs(float(v["vz"])) < 4002
    ]
    out = a.output / source.name
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=names, lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
    result["counts"][source.name] = {
        "keep": len(kept),
        "outside_tracker": len(rows) - len(kept),
    }
    result["sha256"][source.name] = hashlib.sha256(out.read_bytes()).hexdigest()
    result["source_sha256"][source.name] = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
(a.output / "selection.json").write_text(json.dumps(result, indent=2) + "\n")
