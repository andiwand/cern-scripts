"""Archive selected validation outputs; retain hashes instead of duplicate CSVs."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--records", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    p.error("Refusing to overwrite archived results")
a.output.mkdir(parents=True)
selected = ["pruned-check", "helix-refine", "helix-fine", "probe-input", "probe-cache", "probe-reference025", "probe-helix-refine", "probe-helix-fine-ok", "probe-helix20"]
duplicates = ["cache-check", "localcache-check", "helix-final-replay"] + [Path(r["output"]).name for r in json.loads((a.work / "repeated-timings.json").read_text())]
for name in selected + duplicates:
    src, dst = a.work / name, a.output / name
    dst.mkdir()
    hashes = {}
    for f in src.iterdir():
        if f.suffix == ".csv" and f.name.startswith("event"):
            with f.open("rb") as stream:
                hashes[f.name] = hashlib.file_digest(stream, "sha256").hexdigest()
            if name in selected:
                with f.open("rb") as stream, gzip.open(dst / (f.name + ".gz"), "wb", compresslevel=6) as zipped:
                    shutil.copyfileobj(stream, zipped)
        elif f.suffix in [".csv", ".json"]:
            shutil.copy2(f, dst / f.name)
    (dst / "csv-hashes.json").write_text(json.dumps(hashes, indent=2))
    for suffix in [".log", ".command.json"]:
        f = src.with_suffix(suffix)
        if f.exists(): shutil.copy2(f, a.output / f.name)
for name in ["repeated-timings.json"]:
    shutil.copy2(a.work / name, a.output / name)
for f in (a.work / "report").iterdir():
    if f.suffix in [".pdf", ".json"]: shutil.copy2(f, a.output / f.name)
records = a.output / "records"
records.mkdir()
for f in a.records.iterdir():
    if f.suffix in [".log", ".json"]:
        shutil.copy2(f, records / f.name)
binary_hashes = {}
for name in ["baseline-build", "cache-build", "localcache-build", "pruned-build", "helix-refine-build", "helix-fine-build", "helix-final-build"]:
    dst = records / name
    dst.mkdir()
    for f in (a.work / name).iterdir():
        if f.suffix in [".hpp", ".cpp", ".json"]: shutil.copy2(f, dst / f.name)
        elif f.suffix == ".so": binary_hashes[name] = hashlib.sha256(f.read_bytes()).hexdigest()
for name in ["probe-trace.log", "probe-helix025.log", "helix025-check.log"]:
    if (a.work / name).exists(): shutil.copy2(a.work / name, records / name)
provenance = {
    "source": str(a.source),
    "acts_revision": subprocess.check_output(["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True).strip(),
    "numerical_physics_revision": "d419e58b19705e27081e9c718f7c9ead9ddf6f98",
    "binary_sha256": binary_hashes,
    "limitations": "Frozen ABI bridge, immutable geometry, one worker. Exact-output optimisation accepted; helix remains experimental. No full ACTS rebuild/CI or digitisation/reconstruction validation. Reference main/G4 are archived, not rerun.",
}
(a.output / "provenance.json").write_text(json.dumps(provenance, indent=2))
inventory = {str(f.relative_to(a.output)): {"bytes": f.stat().st_size, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()} for f in a.output.rglob("*") if f.is_file()}
(a.output / "inventory.json").write_text(json.dumps(inventory, indent=2))
print(f"Archived {sum(r['bytes'] for r in inventory.values()) / 2**20:.1f} MiB of validation output; no physics input files")
