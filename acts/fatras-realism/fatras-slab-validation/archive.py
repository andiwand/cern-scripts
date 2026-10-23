"""Preserve slab validation evidence; nothing here is a runtime physics input."""

import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    p.error("Refusing to overwrite evidence archive")
a.output.mkdir(parents=True)
for name in ["runs", "refined", "attribution", "replay", "final-build"]:
    shutil.copytree(a.work / name, a.output / name)
for name in [
    "analysis.json",
    "replay-checks.json",
    "slab-validation.pdf",
    "build-final.log",
    "run.log",
    "refine.log",
    "attribute.log",
    "verify.log",
    "slab",
    "slab-scan",
    "slab-refined",
    "slab.cpp",
    "slab-scan.cpp",
    "slab-refined.cpp",
    "build.json",
]:
    shutil.copy2(a.work / name, a.output / name)
shutil.copytree(
    Path(__file__).parent,
    a.output / "tools",
    ignore=shutil.ignore_patterns("results", "__pycache__"),
)
revision = {
    "acts_commit": subprocess.check_output(
        ["git", "-C", str(a.source), "rev-parse", "HEAD"], text=True
    ).strip(),
    "tools_commit": subprocess.check_output(
        ["git", "-C", str(Path(__file__).parent), "rev-parse", "HEAD"], text=True
    ).strip(),
}
(a.output / "revision.json").write_text(json.dumps(revision, indent=2))
# Preserve exact current implementation sources alongside external code.
for name in [
    "Fatras/include/ActsFatras/Kernel/detail/SimulationActor.hpp",
    "Fatras/include/ActsFatras/Kernel/SingleParticleSimulationResult.hpp",
    "Fatras/include/ActsFatras/Physics/ElectroMagnetic/Ionisation.hpp",
    "Fatras/include/ActsFatras/Physics/ElectroMagnetic/Bremsstrahlung.hpp",
    "Fatras/include/ActsFatras/Physics/ElectroMagnetic/ComptonScattering.hpp",
    "Fatras/include/ActsFatras/Physics/ElectroMagnetic/PhotonConversion.hpp",
    "Fatras/include/ActsFatras/Physics/ElectroMagnetic/detail/Highland.hpp",
    "Fatras/src/Physics/Ionisation.cpp",
    "Fatras/src/Physics/Bremsstrahlung.cpp",
    "Fatras/src/Physics/ComptonScattering.cpp",
    "Core/src/Material/Interactions.cpp",
]:
    out = a.output / "source" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.source / name, out)
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
