import argparse, json, shlex, subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--acts-source", type=Path, required=True)
p.add_argument("--acts-build", type=Path, required=True)
p.add_argument("--geant4-lib", type=Path, required=True)
a = p.parse_args()
b = a.acts_build
g = a.geant4_lib
old = next(
    line.split("=", 1)[1]
    for line in (b / "CMakeCache.txt").read_text().splitlines()
    if line.startswith("CMAKE_HOME_DIRECTORY:")
)
e = next(
    x
    for x in json.loads((b / "compile_commands.json").read_text())
    if x["file"].endswith("/Geant4DecayTests.cpp")
)
f = shlex.split(e["command"])
args = []
i = 0
while i < len(f):
    if f[i] in ["-o", "-c"]:
        i += 2
        continue
    if f[i] == "-g" or f[i].startswith("-DBOOST"):
        i += 1
        continue
    args.append(f[i].replace(old, str(a.acts_source)))
    i += 1
cmd = args + [
    str(a.source),
    str(a.acts_source / "Fatras/Geant4/src/Geant4NuclearInteraction.cpp"),
    "-o",
    str(a.output),
]
cmd += (
    [str(b / "lib" / ("lib" + n + ".dylib")) for n in ["ActsFatras", "ActsCore"]]
    + [str(x) for x in g.glob("libG4*.dylib")]
    + [
        str(g / "libCLHEP.dylib"),
        "-Wl,-rpath," + str(b / "lib"),
        "-Wl,-rpath," + str(g),
    ]
)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.with_suffix(".build.json").write_text(json.dumps(cmd, indent=2))
subprocess.run(cmd, check=True)
