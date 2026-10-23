#!/usr/bin/env python3
"""Build the standalone probe against an MT-enabled Geant4 installation."""

import argparse
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--geant4-config", default="geant4-config")
p.add_argument("--compiler", default="clang++")
p.add_argument("--output", type=Path, required=True)
p.add_argument("--sanitizer", choices=["address", "thread"])
a = p.parse_args()
source = Path(__file__).with_name("direct-model.cpp")
flags = shlex.split(
    subprocess.check_output([a.geant4_config, "--cflags", "--libs"], text=True)
)
# No run manager, event loop, tracking manager or physics-list library.
components = {
    "G4processes",
    "G4particles",
    "G4materials",
    "G4track",
    "G4geometry",
    "G4global",
    "G4intercoms",
}
flags = [
    f
    for f in flags
    if not f.startswith("-l") or f[2:] in components or f.startswith("-lCLHEP")
]
rpaths = ["-Wl,-rpath," + f[2:] for f in flags if f.startswith("-L")]
cmd = [a.compiler, "-O2", "-g", *flags, *rpaths, str(source), "-o", str(a.output)]
if a.sanitizer:
    cmd += ["-fsanitize=" + a.sanitizer, "-fno-omit-frame-pointer"]
a.output.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(cmd, check=True)
a.output.with_suffix(".build.json").write_text(
    json.dumps(
        {
            "command": cmd,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "compiler": subprocess.check_output([a.compiler, "--version"], text=True),
            "geant4_version": subprocess.check_output(
                [a.geant4_config, "--version"], text=True
            ).strip(),
            "sanitizer": a.sanitizer,
            "geant4_libraries_instrumented": False,
        },
        indent=2,
    )
    + "\n"
)
