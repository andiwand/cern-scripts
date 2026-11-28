"""Review the frozen hole/outlier scan and extract primary-pass counters."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
from analyze import load

root = Path(sys.argv[1])
scripts = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


design = read(root / "design.json")
frozen = read(root / "frozen-plan.json")
training = read(root / "training.json")
validation = read(root / "validation.json")
previous_plan = read(root.parent / "nn-extended/training.json")
previous_validation = read(root.parent / "nn-extended/validation.json")
equal_cut = []
for prefix in ["core10u10", "tail5u5"]:
    variants = [prefix + "h1o1", prefix + "h1o2"]
    first, second = [load(root / "training" / v) for v in variants]
    differences = []
    for group in "PRE":
        assert first[group].dtype == second[group].dtype
        assert first[group].shape == second[group].shape
        for field in first[group].dtype.names:
            floating = np.issubdtype(first[group][field].dtype, np.inexact)
            if not np.array_equal(
                first[group][field], second[group][field], equal_nan=floating
            ):
                differences.append(group + "." + field)
    equal_cut.append(
        dict(variants=variants, differences=differences, exact=not differences)
    )
(root / "equal-cut-check.json").write_text(json.dumps(equal_cut, indent=2) + "\n")
assert all(c["exact"] for c in equal_cut)
assert (root / "exit-code").read_text().strip() == "0"
assert not (root / "STOP").exists()
assert sha(root / "design.json") == frozen["design_sha256"]
assert sha(root / "training.json") == frozen["training_sha256"]
assert sha(root.parent / "training.json") == design["original_plan_sha256"]
assert sha(root.parent / "nn-extended/training.json") == design["baseline_plan_sha256"]
assert len(design["variants"]) == 22
counters = {}
audits = {}
names = [
    "Input seeds",
    "Used seeds",
    "Duplicate seeds",
    "CKF tracks",
    "selected tracks",
    "Seeds with more than one branch",
    "Total shared hits",
    "resolved tracks",
    "Stopped tracks reaching max holes",
    "Stopped tracks below pT cut",
]
for stage in ["training", "validation"]:
    for path in sorted((root / stage).iterdir()):
        if not path.is_dir():
            continue
        assert (path / "exit-code").read_text().strip() == "0"
        if path.name in design["variants"]:
            audit = read(path / "scan-audit.json")
            assert audit["events"] == (200 if stage == "training" else 800)
            audits[f"{stage}/{path.name}"] = audit
        log = (path / "log.RAWtoALL").read_text()
        for flag, expected in [
            ("scatteringTail", path.name.startswith("tail")),
            ("scatteringTailSecondary", False),
            ("doBremRecovery", False),
        ]:
            assert re.search(rf"Acts\.{flag}\s+: {expected}(?:\s|$)", log), (path, flag)
        counts = {}
        for line in log.splitlines():
            columns = [" ".join(c.split()) for c in line.split("|")[1:-1]]
            if len(columns) > 1 and columns[0] in names and columns[0] not in counts:
                counts[columns[0]] = int(columns[-1])
        assert counts["Seeds with more than one branch"] == 0
        inclusive = (
            training["inclusive"] if stage == "training" else validation["inclusive"]
        )
        assert counts["resolved tracks"] == inclusive[path.name]["tracks"]
        counts["shared_hit_rejected"] = (
            counts["selected tracks"] - counts["resolved tracks"]
        )
        counters[f"{stage}/{path.name}"] = counts
assert len([key for key in audits if key.startswith("training/")]) == 22
unchanged = []
for point, result in validation["points"].items():
    assert set(result["groups"]) == {"core", "previous", "new"}
    for family, group in result["groups"].items():
        choice = training["choices"][point]["groups"][family]
        for key in ["variant", "metric", "cut", "training"]:
            assert choice[key] == group[key]
        assert group["validation"]["events"] == 800
        if choice == previous_plan["choices"][point]["groups"][family]:
            earlier = previous_validation["points"][point]["groups"][family]
            assert group["validation"] == earlier["validation"]
            assert group["resolutions"] == earlier["resolutions"]
            unchanged.append(f"{point}/{family}")
    if training["choices"][point] == previous_plan["choices"][point]:
        assert result == previous_validation["points"][point]
subprocess.run(
    [sys.executable, str(scripts / "check_main_point.py"), str(root)], check=True
)
(root / "candidate-counters.json").write_text(json.dumps(counters, indent=2) + "\n")
(root / "final-audit.json").write_text(
    json.dumps(
        dict(
            checks="Frozen design/plans, all run exits/configuration audits and runtime mode flags, event counts, primary counters and independent main-point counts pass",
            design_sha256=frozen["design_sha256"],
            training_sha256=frozen["training_sha256"],
            validation_sha256=sha(root / "validation.json"),
            runs=audits,
            equal_cut_controls=equal_cut,
            unchanged_choices_checked=unchanged,
            caveat="Evaluation sample previously inspected; no pT selection changes",
        ),
        indent=2,
    )
    + "\n"
)
print("Hole/outlier scan audit passed")
