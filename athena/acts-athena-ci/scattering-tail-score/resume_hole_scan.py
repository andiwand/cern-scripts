"""Resume the frozen scan after its pre-run disk-reserve stop."""

import json
from pathlib import Path
import shutil
import subprocess
import sys

from hole_scan import run_batch, sha

root = Path(sys.argv[1]).absolute()
scripts = Path(__file__).resolve().parent
frozen = json.loads((root / "frozen-plan.json").read_text())
assert sha(root / "training.json") == frozen["training_sha256"]
assert sha(root / "design.json") == frozen["design_sha256"]
assert (root / "exit-code").read_text().strip() == "1"
assert (
    "Less than 12 GiB free before run"
    in (root.parent / "hole-scan.driver.log").read_text()
)
assert shutil.disk_usage(root).free > 16 * 2**30
pending = []
for variant in frozen["validation_variants"]:
    path = root / "validation" / variant
    if path.exists():
        assert (path / "exit-code").read_text().strip() == "0"
    else:
        pending.append(variant)
archive = root / "disk-reserve-stop"
archive.mkdir()
for name in ["exit-code", "review-exit-code", "STOP"]:
    path = root / name
    if path.exists():
        path.rename(archive / name)
(archive / "resume.json").write_text(
    json.dumps(
        dict(
            pending=pending,
            free_bytes=shutil.disk_usage(root).free,
            checks="Frozen choices unchanged; existing evaluation outputs complete; no failed reconstruction output reused",
        ),
        indent=2,
    )
    + "\n"
)
try:
    run_batch(root, "validation", pending, 800, 200, 2)
    with (root / "evaluation.log").open("w") as log:
        subprocess.run(
            [
                sys.executable,
                str(scripts / "nn_analyze.py"),
                "evaluate",
                str(root / "validation"),
                str(root / "validation.json"),
                "--plan",
                str(root / "training.json"),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    (root / "exit-code").write_text("0\n")
    with (root / "audit.log").open("w") as log:
        subprocess.run(
            [sys.executable, str(scripts / "audit_hole_scan.py"), str(root)],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    with (root / "cross-calibration.log").open("w") as log:
        subprocess.run(
            [sys.executable, str(scripts / "cross_nn.py"), str(root.parent), root.name],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
except BaseException:
    if not (root / "exit-code").exists():
        (root / "exit-code").write_text("1\n")
    (root / "review-exit-code").write_text("1\n")
    raise
(root / "review-exit-code").write_text("0\n")
