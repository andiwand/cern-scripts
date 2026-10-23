#!/usr/bin/env python3
"""Restore archived inclusive inputs, requiring an exact SHA256 match per event."""

import argparse, csv, hashlib, json, math
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--reference", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
reference = json.loads(a.reference.read_text())
proof = {}
for source in sorted(a.source.glob("event*-particles.csv")):
    with source.open() as f:
        reader = csv.DictReader(f)
        names = [n for n in reader.fieldnames if not n.startswith("parent_id_")]
        rows = list(reader)
    assert all(
        int(row[k]) == 0 for row in rows for k in row if k.startswith("parent_id_")
    )
    rows = [
        row
        for row in rows
        if math.hypot(float(row["vx"]), float(row["vy"])) < 1202
        and abs(float(row["vz"])) < 4002
    ]
    output = a.output / source.name
    with output.open("w") as f:
        writer = csv.DictWriter(
            f, fieldnames=names, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    assert digest == reference["sha256"][source.name], source.name
    proof[source.name] = digest
selection = dict(reference)
selection["sha256"] = proof
selection["counts"] = {k: reference["counts"][k] for k in proof}
selection["schema_note"] = (
    "Removed only all-zero optional ancestry columns. Inputs match archived SHA256 hashes; only ID birth boundary is applied."
)
(a.output / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
