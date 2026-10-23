"""Archive optional validation output; never create runtime physics data."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    p.error("Refusing to overwrite archive")
a.output.mkdir(parents=True)


def copy(path, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)


full = {"compton-100", "compton-50", "compton-200", "compton-pair-cut", "standard-one"}
runs = full | {
    "disabled-check",
    "repeat-control-1",
    "repeat-control-2",
    "repeat-compton-1",
    "repeat-compton-2",
    "standard-four",
}
for name in sorted(runs):
    directory = a.work / name
    if not (directory / "metadata.json").exists():
        continue
    for path in directory.iterdir():
        if path.suffix == ".csv":
            if name not in full:
                continue
            dest = a.output / name / (path.name + ".gz")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with path.open("rb") as src, gzip.GzipFile(
                filename=str(dest), mode="wb", mtime=0
            ) as dst:
                shutil.copyfileobj(src, dst)
        elif path.suffix == ".json":
            copy(path, a.output / name / path.name)
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.glob("event*.csv")
    }
    (a.output / name / "csv-hashes.json").write_text(json.dumps(hashes, indent=2))
    for suffix in [".command.json", ".log", ".runner.py"]:
        path = directory.with_suffix(suffix)
        if path.exists():
            copy(path, a.output / "records" / path.name)
for name in [
    "analysis.json",
    "measure.py",
    "measure.log",
    "reference.csv",
    "reference-build.json",
    "compton.pdf",
    "checks.json",
    "test-build.json",
    "test.log",
    "regression-build.json",
    "regression.log",
    "bindings-build.json",
    "bindings.log",
    "bridge-build.log",
    "test-compton",
    "test-regressions",
    "compton-reference",
    "test-main.cpp",
    "build-tests.py",
    "regressions.py",
]:
    path = a.work / name
    if path.exists():
        copy(path, a.output / name)
for name in ["bridge", "pruned-build"]:
    shutil.copytree(
        a.work / name, a.output / name, ignore=shutil.ignore_patterns("*.dSYM")
    )
records = a.output / "source"
records.mkdir()
revision = subprocess.check_output(
    ["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True
).strip()
files = subprocess.check_output(
    ["git", "-C", str(a.source), "diff", "--name-only", "d419e58b19..HEAD"], text=True
).splitlines()
for name in files:
    copy(a.source / name, records / name)
(a.output / "revision.json").write_text(
    json.dumps(
        {
            "revision": revision,
            "parent": "d419e58b19",
            "dirty": bool(
                subprocess.check_output(
                    ["git", "-C", str(a.source), "status", "--porcelain"], text=True
                )
            ),
            "kind": "Optional validation archive, not simulation input",
        },
        indent=2,
    )
)
shutil.copytree(
    Path(__file__).resolve().parent,
    a.output / "tools",
    ignore=shutil.ignore_patterns("results", "__pycache__"),
)
inventory = {
    str(path.relative_to(a.output)): {
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    for path in a.output.rglob("*")
    if path.is_file()
}
(a.output / "inventory.json").write_text(json.dumps(inventory, indent=2))
print(a.output, sum(x["bytes"] for x in inventory.values()) / 1024**2, "MiB")
