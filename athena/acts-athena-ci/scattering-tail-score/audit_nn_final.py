"""Review completed NN controls, frozen plans, models and held-out counts."""

import hashlib
import json
import math
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
final = root / "nn-extended"
assert (final / "comparison-exit-code").read_text().strip() == "0"
assert (root / "nn-native/finish-exit-code").read_text().strip() == "0"
assert (final / "exit-code").read_text().strip() == "0"
plans = {}
for name, directory in [
    ("raw", root),
    ("nn-original", root / "nn-native"),
    ("nn-final", final),
]:
    digest = hashlib.sha256((directory / "training.json").read_bytes()).hexdigest()
    assert (
        digest
        == json.loads((directory / "frozen-plan.json").read_text())["training_sha256"]
    )
    plans[name] = digest
models = library = None
runs = {}
for sample in ["training", "validation"]:
    for path in sorted((final / sample).iterdir()):
        if not path.is_dir():
            continue
        assert (path / "exit-code").read_text().strip() == "0", path
        text = (path / "log.RAWtoALL").read_text()
        assert "TAIL_SCORE_NN pre charge=0 size=0" in text, path
        hashes = re.findall(r"TAIL_SCORE_NATIVE_MODEL\s+(\S+)\s+([a-f0-9]{64})", text)
        assert len(hashes) == 4, (path, hashes)
        digest = (path / "library-sha256.txt").read_text().split()[0]
        if models is None:
            models, library = hashes, digest
        assert models == hashes and library == digest, path
        settings = (path / "settings.txt").read_text()
        assert (
            "scatteringTailScoring=True" in settings
            and "doBremRecovery=False" in settings
        )
        tail = path.name.startswith("tail")
        assert f"flags.Acts.scatteringTail={tail};" in settings
        runs[f"{sample}/{path.name}"] = dict(exit_code=0, settings=settings.strip())
# The wider nominal gate must not alter any unchanged working point.
old_plan = json.loads((root / "nn-native/training.json").read_text())
new_plan = json.loads((final / "training.json").read_text())
old_result = json.loads((root / "nn-native/validation.json").read_text())
new_result = json.loads((final / "validation.json").read_text())
for retention, point in new_plan["choices"].items():
    if point == old_plan["choices"][retention]:
        assert (
            new_result["points"][retention] == old_result["points"][retention]
        ), retention
for retention, point in json.loads(
    (root / "nn-native/early-validation.json").read_text()
)["points"].items():
    assert new_result["points"][retention] == point, retention
# Independent vectorized counters must agree with the full evaluator and cross-comparison.
checked = json.loads((final / "main-point-check.json").read_text())
cross = json.loads((final / "cross-calibration.json").read_text())
for family, values in checked.items():
    for key, value in values.items():
        assert cross["counts"]["nn-" + family][key] == value, (family, key)
assert (final / "highpoint-exit-code").read_text().strip() == "0"
raw_result = json.loads((root / "validation.json").read_text())
for retention, name in [
    ("0.995", "cross-calibration.json"),
    ("0.998", "cross-calibration-0.998.json"),
]:
    paired = json.loads((final / name).read_text())
    for prefix, report in [("raw", raw_result), ("nn", new_result)]:
        for family, choice in report["points"][retention]["groups"].items():
            assert paired["counts"][prefix + "-" + family] == choice["validation"], (
                retention,
                prefix,
                family,
            )
    for key, value in new_result["points"][retention]["paired"]["new-core"][
        "rates"
    ].items():
        assert math.isclose(
            paired["paired"]["nn-new minus nn-core"][key],
            value,
            rel_tol=1e-12,
            abs_tol=1e-14,
        ), (retention, key)
report = dict(
    checks="Frozen plans unchanged; all NN exits, calibration mode, model/library hashes and independent counts pass",
    plans=plans,
    models=dict(models),
    library_sha256=library,
    runs=runs,
)
(final / "final-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(report["checks"])
