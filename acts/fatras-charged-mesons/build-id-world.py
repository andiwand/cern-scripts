import argparse, json, shlex, subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--acts-build", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
e = next(
    e
    for e in json.loads((a.acts_build / "compile_commands.json").read_text())
    if e["file"].endswith("/plugins/Geant4.cpp")
)
flags = shlex.split(e["command"])
out = []
i = 0
while i < len(flags):
    if flags[i] in ["-o", "-c"]:
        i += 2
        continue
    if flags[i].startswith("-DActsExamplesPythonBindingsGeant4_EXPORTS"):
        i += 1
        continue
    out.append(flags[i])
    i += 1
g4 = Path("/Users/andreas/cern/source/acts/ci-dependencies/.spack-env/view/lib")
libs = [str(g4 / ("libG4" + name + ".dylib")) for name in ["run", "geometry", "global"]]
subprocess.run(
    [
        *out,
        str(Path(__file__).with_name("id-world.cpp")),
        "-shared",
        "-undefined",
        "dynamic_lookup",
        "-o",
        str(a.output),
        *libs,
        "-Wl,-rpath," + str(a.acts_build / "lib"),
        "-Wl,-rpath," + str(g4),
    ],
    cwd=e["directory"],
    check=True,
)
