import json, shlex, subprocess
from pathlib import Path
import argparse

p = argparse.ArgumentParser(
    description="Build the standalone decay spectrum comparison"
)
p.add_argument("--acts-build", type=Path, required=True)
p.add_argument("--geant4-lib", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
b = a.acts_build
e = next(
    x
    for x in json.loads((b / "compile_commands.json").read_text())
    if x["file"].endswith("/Geant4DecayTests.cpp")
)
f = shlex.split(e["command"])
args = []
i = 0
while i < len(f):
    if f[i] in ("-o", "-c"):
        i += 2
        continue
    if f[i].startswith("-DBOOST"):
        i += 1
        continue
    args.append(f[i])
    i += 1
libs = [
    str(b / "lib" / ("lib" + n + ".dylib"))
    for n in ("ActsFatrasGeant4", "ActsFatras", "ActsCore")
]
g = a.geant4_lib
libs += [str(x) for x in g.glob("libG4*.dylib")]
subprocess.run(
    args
    + [
        str(Path(__file__).with_name("decay-reference.cpp")),
        "-o",
        str(a.output),
        *libs,
        "-Wl,-rpath," + str(b / "lib"),
        "-Wl,-rpath," + str(g),
    ],
    check=True,
)
