"""Archive optional validation evidence; none of it is a runtime physics input."""

import argparse, gzip, hashlib, json, shutil, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    p.error("Refusing to overwrite archive")
a.output.mkdir(parents=True)


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.name.startswith("event") and src.suffix == ".csv":
        with src.open("rb") as f, gzip.open(
            str(dst) + ".gz", "wb", compresslevel=6
        ) as g:
            shutil.copyfileobj(f, g)
    else:
        shutil.copy2(src, dst)


skip_csv = {
    "current-1",
    "current-2",
    "control-0",
    "control-1",
    "control-2",
    "standard-4",
    "geant4-refreshed",
    "birth-column-inclusive",
    "trace-current",
    "optimized-1",
    "optimized-2",
    "optimized-standard-1",
    "optimized-standard-4",
    "fast-stop-0",
}
if (a.work / "optimized-0").exists():
    skip_csv.add("current-0")
if (a.work / "guarded-0").exists():
    skip_csv.update(
        {
            "optimized-0",
            "guarded-1",
            "guarded-2",
            "guarded-standard-1",
            "guarded-standard-4",
            "guarded-standard-4-repeat1",
            "guarded-standard-4-repeat2",
        }
    )
for src in sorted(a.work.rglob("*")):
    if not src.is_file() or "__pycache__" in src.parts or src.suffix == ".png":
        continue
    rel = src.relative_to(a.work)
    top = rel.parts[0]
    if top in [
        "trace-build",
        "birth-column-build",
        "stopping-build",
        "final-build",
        "optimized-build",
        "fast-stop-build",
    ] and src.suffix not in [".hpp", ".cpp", ".json"]:
        continue
    if src.name.startswith("event") and src.suffix == ".csv" and top in skip_csv:
        continue
    copy(src, a.output / rel)
for directory in a.work.iterdir():
    if not directory.is_dir():
        continue
    files = list(directory.glob("event*.csv"))
    if files:
        manifest = {
            f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)
        }
        dst = a.output / directory.name / "csv-sha256.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(manifest, indent=2))
commit = subprocess.check_output(
    ["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True
).strip()
for name in subprocess.check_output(
    ["git", "-C", str(a.source), "diff", "--name-only", "0429b7c1e1", commit], text=True
).splitlines():
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
print(len(files), "files;", sum(v["bytes"] for v in files.values()) / 1024**2, "MiB")
