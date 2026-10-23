#!/usr/bin/env python3
"""Verify a CSV ancestry-only replay against the previously archived simulation."""
import argparse
import hashlib
import json
from itertools import zip_longest
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--baseline", type=Path, required=True)
p.add_argument("--current", type=Path, required=True)
p.add_argument("--events", type=int, default=20)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
rows = []
for event in range(a.events):
    stem = f"event{event:09d}"
    hit_file = f"{stem}-hits.csv"
    old_hash = hashlib.sha256((a.baseline / hit_file).read_bytes()).hexdigest()
    new_hash = hashlib.sha256((a.current / hit_file).read_bytes()).hexdigest()
    assert old_hash == new_hash, f"changed hits: event {event}"
    particle_file = f"{stem}-particles_simulated.csv"
    with (a.baseline / particle_file).open("rb") as old, (
        a.current / particle_file
    ).open("rb") as new:
        header = old.readline().rstrip()
        columns = len(header.split(b","))
        assert b",".join(new.readline().rstrip().split(b",")[:columns]) == header
        count = 0
        for count, (left, right) in enumerate(zip_longest(old, new), 1):
            assert (
                left is not None and right is not None
            ), f"changed row count: event {event}"
            assert left.rstrip() == b",".join(
                right.rstrip().split(b",")[:columns]
            ), f"changed truth: event {event}, row {count}"
    rows.append(
        {
            "event": event,
            "hit_sha256": new_hash,
            "truth_rows": count,
            "preexisting_truth_columns_identical": True,
        }
    )
    print(event, count, "identical", flush=True)
a.output.write_text(
    json.dumps(
        {"baseline": str(a.baseline), "current": str(a.current), "events": rows},
        indent=2,
    )
    + "\n"
)
