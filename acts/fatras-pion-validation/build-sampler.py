import argparse, json, shlex, subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--acts-build", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
e = next(
    e
    for e in json.loads((a.acts_build / "compile_commands.json").read_text())
    if e["file"].endswith("/FatrasSimulationTests.cpp")
)
flags = shlex.split(e["command"])
result = []
i = 0
while i < len(flags):
    if flags[i] in ("-o", "-c"):
        i += 2
        continue
    if flags[i].startswith("-DBOOST"):
        i += 1
        continue
    result.append(flags[i])
    i += 1
libraries = []
for name in ("ActsFatras", "ActsCore"):
    libraries.append(
        str(
            next(
                p
                for p in (a.acts_build / "lib").glob(f"lib{name}.*")
                if p.suffix in (".dylib", ".so", ".a")
            )
        )
    )
subprocess.run(
    [
        *result,
        str(Path(__file__).with_name("sample-collisions.cpp")),
        "-o",
        str(a.output),
        *libraries,
        "-Wl,-rpath," + str(a.acts_build / "lib"),
    ],
    cwd=e["directory"],
    check=True,
)
