"""Preserve validation evidence without turning it into runtime physics data."""

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
p.add_argument("--diagnostics", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    p.error("Refusing to overwrite archive")
a.output.mkdir(parents=True)


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.name.endswith(".csv") and src.name.startswith("event"):
        dst = dst.with_name(dst.name + ".gz")
        with src.open("rb") as incoming, gzip.open(
            dst, "wb", compresslevel=6
        ) as outgoing:
            shutil.copyfileobj(incoming, outgoing)
    else:
        shutil.copy2(src, dst)


for src in sorted(a.work.rglob("*")):
    if not src.is_file() or src.name.endswith(".png"):
        continue
    rel = src.relative_to(a.work)
    top = rel.parts[0]
    if src.name.startswith("event") and src.suffix == ".csv":
        if "-repeat-" in top or top in ["standard-4", "geant4-refreshed"]:
            continue
    copy(src, a.output / rel)
for directory in sorted(a.work.iterdir()):
    if not directory.is_dir():
        continue
    csvs = list(directory.glob("event*.csv"))
    if not csvs:
        continue
    manifest = {
        f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(csvs)
    }
    dest = a.output / directory.name / "csv-sha256.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(manifest, indent=2))
# Preserve diagnostic summaries, kernel tests and exact commands. Full exploratory
# event outputs remain at their recorded paths; they are not accepted references.
for pattern in [
    "*.py",
    "*.cpp",
    "*.json",
    "*tests.log",
    "legacy-test.log",
    "regressions.log",
    "bindings.log",
    "*.csv",
    "test-*",
]:
    for src in a.diagnostics.glob(pattern):
        if src.is_file():
            copy(src, a.output / "diagnostics" / src.name)
for folder in ["explicit-build", "radiation-first-build", "coupled-build"]:
    for src in (a.diagnostics / folder).rglob("*"):
        if src.suffix in [".json", ".hpp", ".cpp"]:
            copy(
                src,
                a.output
                / "diagnostics"
                / folder
                / src.relative_to(a.diagnostics / folder),
            )
for name in ["explicit-inclusive", "radiation-first", "coupled-inclusive"]:
    src = a.diagnostics / name / "metadata.json"
    if src.exists():
        copy(src, a.output / "diagnostics" / name / "metadata.json")
commit = subprocess.check_output(
    ["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True
).strip()
files = subprocess.check_output(
    [
        "git",
        "-C",
        str(a.source),
        "diff",
        "--name-only",
        "45def224e3395120efe780bc767a8b95f829cb9b",
        commit,
    ],
    text=True,
).splitlines()
for name in files:
    copy(a.source / name, a.output / "source" / name)
for src in Path(__file__).parent.iterdir():
    if src.is_file():
        copy(src, a.output / "tools" / src.name)
(a.output / "revision.json").write_text(
    json.dumps(
        {
            "acts_commit": commit,
            "tools_commit": subprocess.check_output(
                ["git", "-C", str(Path(__file__).parent), "rev-parse", "HEAD"],
                text=True,
            ).strip(),
            "prototype_scope": "Diagnostic summaries and source snapshots; only current is accepted. Legacy-fixed is an ablation.",
        },
        indent=2,
    )
)
files = {
    str(f.relative_to(a.output)): {
        "bytes": f.stat().st_size,
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
    }
    for f in sorted(a.output.rglob("*"))
    if f.is_file()
}
(a.output / "inventory.json").write_text(json.dumps(files, indent=2))
print(f'{len(files)} files; {sum(f["bytes"] for f in files.values())/1024**2:.1f} MiB')
