#!/usr/bin/env python3
"""Build only a private replacement library using the original Ninja commands.

No files in athena-tail or athena-build-tail are changed. Only the component
translation unit instantiates the NN calibrator in this library. All other
objects and all compiler/linker options come from the validated study build.
"""
from pathlib import Path
import difflib
import hashlib
import json
import shlex
import shutil
import subprocess

A = Path("/home/astefl/source/acts/acts-athena-ci")
B = A / "athena-build-tail-score"
old = A / "athena-tail-score/Tracking/Acts/ActsTrackReconstruction"
out = A / "run/scattering-tail-score/nn-control"
src = out / "src/ActsTrackReconstruction"
assert not src.exists(), f"Refusing to overwrite {src}"
shutil.copytree(old, src)
(out / "lib").mkdir()
changes = {
    "src/detail/NNPixelClusterInputHelpers.h": [
        (
            "if (cell.isValid())\n      nn.setPixelXPitch(i, design->parameters(cell).width().xPhi());",
            "if (cell.isValid()) {\n      nn.setPixelXPitch(i, design->parameters(cell).width().xPhi());\n      nn.setPixelYPitch(i, design->parameters(cell).width().xEta());\n    }",
        )
    ],
    "src/detail/NNClusterCalibratorToolImpl.icc": [
        ("positions.xprec(maxProbNumberIndex)", "positions.xprec(chosen)"),
        ("positions.yprec(maxProbNumberIndex)", "positions.yprec(chosen)"),
    ],
}
diff = []
for name, edits in changes.items():
    p = src / name
    before = p.read_text()
    after = before
    for a, b in edits:
        assert after.count(a) == 1, (name, a)
        after = after.replace(a, b)
    p.write_text(after)
    diff.extend(
        difflib.unified_diff(
            before.splitlines(True),
            after.splitlines(True),
            fromfile="a/" + name,
            tofile="b/" + name,
        )
    )
(out / "nn-fixes.patch").write_text("".join(diff))
obj = "Tracking/Acts/ActsTrackReconstruction/CMakeFiles/ActsTrackReconstruction.dir/src/components/ActsTrackReconstruction_entries.cxx.o"
lib = "x86_64-el9-gcc15-opt/lib/libActsTrackReconstruction.so"
newobj = str(out / "entries.o")
newlib = str(out / "lib/libActsTrackReconstruction.so")


def command(target):
    return subprocess.check_output(
        ["ninja", "-t", "commands", target], cwd=B, text=True
    ).splitlines()[-1]


compile_original = command(obj)
link_original = command(lib)
cargs = [
    t.replace(str(old), str(src)).replace(obj, newobj)
    for t in shlex.split(compile_original)
]
# Retain the linker invocation, omit CMake's following debug-strip/install steps.
largs = shlex.split(link_original)[2:]
largs = largs[: largs.index("&&")]
largs = [newobj if t == obj else newlib if t == lib else t for t in largs]
assert cargs[cargs.index("-o") + 1] == newobj
assert largs[largs.index("-o") + 1] == newlib
assert newobj in largs
(out / "commands.json").write_text(
    json.dumps(
        dict(
            compile_original=compile_original,
            link_original=link_original,
            compile=cargs,
            link=largs,
        ),
        indent=2,
    )
)
print("Compiling private NN control", flush=True)
subprocess.run(cargs, cwd=B, check=True)
print("Linking private NN control", flush=True)
subprocess.run(largs, cwd=B, check=True)
(out / "sha256.json").write_text(
    json.dumps(
        {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [B / lib, Path(newlib), out / "nn-fixes.patch"]
        },
        indent=2,
    )
)
print("Control ready:", newlib, flush=True)
