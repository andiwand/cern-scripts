#!/usr/bin/env python3
"""Audit training-only choices before any held-out reconstruction is launched."""
import hashlib
import json
from pathlib import Path
import sys
from analyze import load, counts, check_same

root = Path(sys.argv[1])
plan_path = root / "training.json"
plan = json.loads(plan_path.read_text())
variants = ["core4", "core5", "core7", "core10", "tail4", "tail5", "tail7"]
data = {v: load(root / "training" / v) for v in variants}
check_same(data)
for v, d in data.items():
    assert len(d["E"]) == 200, v
    assert (root / "training" / v / "exit-code").read_text().strip() == "0", v
assert len(plan["events"]) == 200
for point in plan["choices"].values():
    for family, c in point["groups"].items():
        result = counts(data[c["variant"]], c["metric"], c["cut"])
        assert result == c["training"], (family, c)
        assert result["matched"] >= point["target"], (family, c)
assert set(plan["choices"]["0.995"]["groups"]) == {"core", "previous", "new"}
assert not (root / "validation").exists(), "Held-out directory already exists"
selected = sorted(
    {c["variant"] for p in plan["choices"].values() for c in p["groups"].values()}
    | {"core7"}
)
record = dict(
    training_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
    validation_variants=selected,
    training_events=200,
    validation_events=800,
    validation_skip=200,
    checks="All reconstruction exits, shared truth, score dimensions, recomputed training counts, retained-match targets; no held-out directory before freeze",
)
(root / "frozen-plan.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2), flush=True)
