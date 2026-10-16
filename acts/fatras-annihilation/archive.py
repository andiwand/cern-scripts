"""Store validation evidence; preserve one event sample and hashes of replays."""

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    p.error("Refusing to overwrite archive")
a.output.mkdir(parents=True)
for f in sorted(a.work.rglob("*")):
    if not f.is_file() or "__pycache__" in f.parts:
        continue
    rel = f.relative_to(a.work)
    if len(rel.parts) == 1 and f.suffix == ".py" and not f.name.endswith(".runner.py"):
        continue
    accepted = {
        "runtime-build",
        "slabs",
        "current-0",
        "current-1",
        "current-2",
        "control-0",
        "control-1",
        "control-2",
        "standard-1",
        "standard-4",
        "disabled",
        "slab-build",
    }
    if len(rel.parts) > 1 and rel.parts[0] not in accepted:
        continue
    if f.suffix == ".so" and rel.parts[0] != "runtime-build":
        continue
    if f.name.startswith("event") and f.suffix == ".csv":
        if rel.parts[0] != "current-0":
            continue
        target = a.output / (str(rel) + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        with f.open("rb") as src, gzip.open(target, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst)
    elif f.suffix in [".json", ".csv", ".log", ".py", ".cpp", ".hpp", ".pdf", ".so"]:
        target = a.output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
for folder in a.work.iterdir():
    if not folder.is_dir():
        continue
    files = list(folder.glob("event*.csv"))
    if files:
        target = a.output / folder.name / "csv-sha256.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    f.name: hashlib.file_digest(f.open("rb"), "sha256").hexdigest()
                    for f in files
                },
                indent=2,
            )
        )
for name in subprocess.check_output(
    ["git", "-C", str(a.source), "diff", "--name-only", "120acbe04e", "HEAD"], text=True
).splitlines():
    target = a.output / "source" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.source / name, target)
(a.output / "source.patch").write_bytes(
    subprocess.check_output(["git", "-C", str(a.source), "diff", "120acbe04e", "HEAD"])
)
for f in Path(__file__).parent.iterdir():
    if f.is_file():
        target = a.output / "tools" / f.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
(a.output / "revision.json").write_text(
    json.dumps(
        {
            "acts_commit": subprocess.check_output(
                ["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True
            ).strip(),
            "tools_commit": subprocess.check_output(
                ["git", "-C", str(Path(__file__).parent), "rev-parse", "HEAD"],
                text=True,
            ).strip(),
        },
        indent=2,
    )
)
for rel in [
    "fatras-radiative-secondaries/build.py",
    "fatras-radiative-secondaries/run.py",
    "fatras-slab-validation/build.py",
    "fatras-slab-validation/slab.cpp",
]:
    f = Path(__file__).parent.parent / rel
    target = a.output / "shared-tools" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, target)
inventory = {
    str(f.relative_to(a.output)): {
        "bytes": f.stat().st_size,
        "sha256": hashlib.file_digest(f.open("rb"), "sha256").hexdigest(),
    }
    for f in sorted(a.output.rglob("*"))
    if f.is_file()
}
(a.output / "inventory.json").write_text(json.dumps(inventory, indent=2))
print(
    len(inventory),
    "files;",
    sum(v["bytes"] for v in inventory.values()) / 1024**2,
    "MiB",
)
