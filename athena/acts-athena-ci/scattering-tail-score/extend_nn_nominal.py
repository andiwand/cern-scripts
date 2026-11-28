"""Freeze the wider nominal comparator using training data only; retain tail choices."""

import hashlib
import json
from pathlib import Path
import sys
from analyze import load, check_same
from nn_analyze import counts

root = Path(sys.argv[1])
extended = root / "nn-extended"
old = json.loads((root / "nn-native/training.json").read_text())
new = json.loads((extended / "training.json").read_text())
d = load(extended / "training/core14")
assert (extended / "training/core14/exit-code").read_text().strip() == "0"
check_same({"wide": d, "original": load(root / "nn-native/training/core10")})
for r, point in new["choices"].items():
    for family in ["previous", "new"]:
        assert point["groups"][family] == old["choices"][r]["groups"][family]
    for family, c in point["groups"].items():
        data = load(extended / "training" / c["variant"])
        assert counts(data, c["metric"], c["cut"]) == c["training"]
        assert c["training"]["matched"] >= point["target"]
record = dict(
    training_sha256=hashlib.sha256(
        (extended / "training.json").read_bytes()
    ).hexdigest(),
    original_training_sha256=hashlib.sha256(
        (root / "nn-native/training.json").read_bytes()
    ).hexdigest(),
    added_nominal_gate="14/20 sigma",
    validation_events=800,
    validation_skip=200,
    checks="Training-only extension; identical physical truth and unchanged tail choices. Reuse previously frozen validation outputs for existing settings.",
)
(extended / "frozen-plan.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2), flush=True)
