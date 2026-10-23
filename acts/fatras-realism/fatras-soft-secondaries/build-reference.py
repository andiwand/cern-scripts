"""Compile the analytic G4 ionisation comparison using an existing ACTS build."""

import argparse, json, shlex, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--geant4-lib", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
old = next(
    x.split("=", 1)[1]
    for x in (a.build / "CMakeCache.txt").read_text().splitlines()
    if x.startswith("CMAKE_HOME_DIRECTORY:")
)
e = next(
    x
    for x in json.loads((a.build / "compile_commands.json").read_text())
    if x["file"].endswith("/Geant4DecayTests.cpp")
)
f = shlex.split(e["command"])
args = []
i = 0
while i < len(f):
    if f[i] in ["-o", "-c"]:
        i += 2
        continue
    if f[i] == "-g" or f[i].startswith("-DBOOST_TEST"):
        i += 1
        continue
    args.append(f[i].replace(old, str(a.source)))
    i += 1
cmd = (
    args
    + [
        str(Path(__file__).with_name("ionisation-reference.cpp")),
        str(a.source / "Fatras/src/Physics/Ionisation.cpp"),
        "-o",
        str(a.output / "ionisation-reference"),
    ]
    + [
        str(a.build / "lib" / ("lib" + n + ".dylib"))
        for n in ["ActsFatras", "ActsCore"]
    ]
    + [str(x) for x in a.geant4_lib.glob("libG4*.dylib")]
    + [
        str(a.geant4_lib / "libCLHEP.dylib"),
        "-Wl,-rpath," + str(a.build / "lib"),
        "-Wl,-rpath," + str(a.geant4_lib),
    ]
)
(a.output / "reference-build.json").write_text(json.dumps(cmd, indent=2))
subprocess.run(cmd, check=True)
