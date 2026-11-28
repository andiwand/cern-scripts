"""Compile sizeof probes with the experiment's own include paths."""
import json
import os
import shlex
import subprocess
from pathlib import Path

base = Path(os.environ.get("ACTS_EDM_EXPERIMENT_ROOT", "/private/tmp/acts-edm-2026-10-31"))
for variant in ["vector", "any"]:
    entries = json.loads((base / f"build-{variant}/compile_commands.json").read_text())
    entry = next(e for e in entries if e["file"].endswith("/TrackFindingAlgorithmFunction.cpp"))
    args = shlex.split(entry["command"])
    index = args.index("-o")
    del args[index:index + 2]
    args.remove("-c")
    args.remove(entry["file"])
    args += [str(base / "size.cpp"), "-o", str(base / f"size-{variant}")]
    subprocess.run(args, cwd=entry["directory"], check=True)
    output = subprocess.check_output([str(base / f"size-{variant}")], text=True)
    (base / "results" / f"size-{variant}.txt").write_text(output)
    print(variant, output)
