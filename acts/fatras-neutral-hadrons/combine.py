#!/usr/bin/env python3
"""Concatenate disjoint V1 table channels, preserving each channel verbatim."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("inputs", type=Path, nargs="+")
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    p.error("output already exists")
count = 0
bodies = []
sources = []
for source in a.inputs:
    raw = source.read_bytes()
    magic, n, body = raw.split(b"\n", 2)
    if magic != b"ACTS_FATRAS_NUCLEAR_V1":
        p.error(f"unknown format: {source}")
    count += int(n)
    bodies.append(body)
    sources.append(
        {"path": str(source.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}
    )
raw = b"ACTS_FATRAS_NUCLEAR_V1\n" + str(count).encode() + b"\n" + b"\n".join(bodies)
a.output.write_bytes(raw)
a.output.with_suffix(".json").write_text(
    json.dumps(
        {
            "sources": sources,
            "table_sha256": hashlib.sha256(raw).hexdigest(),
            "validation": "Run check.cpp with ACTS to validate channels and conservation before use.",
        },
        indent=2,
    )
    + "\n"
)
