#!/usr/bin/env python3
"""Audit training-only choices and hash the plan before any held-out reconstruction.

usage: freeze.py RUN [--also core7 ...] [--extends PARENT] [--validation-events 800] [--validation-skip 200]
RUN holds training/<variant>/ and training.json (analyze.py tune). Checks every training exit
code, shared truth and score dimensions, the event count, recomputed training counts and
match targets, and that RUN/validation does not exist yet. Writes RUN/frozen-plan.json whose
validation_variants are the chosen variants plus --also.
--extends PARENT: RUN's training pool is PARENT's plus new variants (e.g. a wider core gate).
Families (core / tail) without a new variant must keep PARENT's choices.
"""
import argparse
import hashlib
import json
from pathlib import Path
from analyze import load, counts, check_same

ap = argparse.ArgumentParser()
ap.add_argument("root", type=Path)
ap.add_argument("--also", nargs="*", default=[], help="always validate these variants")
ap.add_argument("--extends", type=Path)
ap.add_argument("--validation-events", type=int, default=800)
ap.add_argument("--validation-skip", type=int, default=200)
a = ap.parse_args()
root = a.root
plan_path = root / "training.json"
plan = json.loads(plan_path.read_text())
variants = sorted(d.name for d in (root / "training").iterdir() if d.is_dir())
data = {v: load(root / "training" / v) for v in variants}
check_same(data)
events = len(plan["events"])
for v, d in data.items():
    assert len(d["E"]) == events, v
    assert (root / "training" / v / "exit-code").read_text().strip() == "0", v
for point in plan["choices"].values():
    for family, c in point["groups"].items():
        result = counts(data[c["variant"]], c["metric"], c["cut"])
        assert result == c["training"], (family, c)
        assert result["matched"] >= point["target"], (family, c)
assert set(plan["choices"]["0.995"]["groups"]) == {"core", "previous", "new"}
assert not (root / "validation").exists(), "Held-out directory already exists"
selected = sorted(
    {c["variant"] for p in plan["choices"].values() for c in p["groups"].values()}
    | set(a.also)
)
record = dict(training_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest())
if a.extends:
    parent_path = a.extends / "training.json"
    parent = json.loads(parent_path.read_text())
    old = {d.name for d in (a.extends / "training").iterdir() if d.is_dir()}
    added = sorted(set(variants) - old)
    changed = {("core" if v.startswith("core") else "tail") for v in added}
    for r, point in plan["choices"].items():
        for family, c in point["groups"].items():
            if ("core" if family == "core" else "tail") not in changed:
                assert c == parent["choices"][r]["groups"][family], (r, family)
    record.update(
        parent_training_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),
        added_variants=added,
    )
record.update(
    validation_variants=selected,
    training_events=events,
    validation_events=a.validation_events,
    validation_skip=a.validation_skip,
    checks="All reconstruction exits, shared truth, score dimensions, recomputed training counts, retained-match targets; no held-out directory before freeze",
)
(root / "frozen-plan.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2), flush=True)
