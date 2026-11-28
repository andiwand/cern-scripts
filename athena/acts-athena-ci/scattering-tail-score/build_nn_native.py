"""Isolated adapter to the existing native kernel; reuse validated object files."""

from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess

A = Path("/home/astefl/source/acts/acts-athena-ci")
R = A / "run/scattering-tail-score"
old = R / "nn-control"
out = R / "nn-native-control"
assert not out.exists()
src = out / "src/ActsTrackReconstruction"
shutil.copytree(old / "src/ActsTrackReconstruction", src)
(out / "lib").mkdir()
shutil.copy2(
    Path(__file__).with_name("NativeStudyNN.h"), src / "src/detail/NativeStudyNN.h"
)
p = src / "src/detail/NNClusterCalibratorToolImpl.icc"
before = p.read_text()
after = before.replace(
    "#include <onnxruntime_cxx_api.h>",
    '#include <onnxruntime_cxx_api.h>\n#include "NativeStudyNN.h"',
)
needle = """std::array<float, 3> probabilities = NNPixelCluster::predictNumberOfClusters(
      *m_options.m_models->numberNetwork, nnInput);"""
assert after.count(needle) == 1
after = after.replace(
    needle,
    """std::array<float, 3> probabilities;
  tailScoreStudy::infer(0, nnInput.payload(), probabilities);""",
)
start = after.index("  Ort::Session& session = selectPositionNetwork(number);")
end = after.index("\n}", start)
after = (
    after[:start]
    + """  std::array<float, 15> output;
  tailScoreStudy::infer(number, nn.payload(), std::span(output).first(5 * number));
  return PositionNNoutput(output.data(), output.data() + 5 * number);
"""
    + after[end:]
)
p.write_text(after)
(out / "adapter.patch").write_text(
    "".join(
        difflib.unified_diff(
            before.splitlines(True),
            after.splitlines(True),
            fromfile="a/" + p.name,
            tofile="b/" + p.name,
        )
    )
)
native = A / "athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool"
objects = []
for name in [
    "NativePixelClusterNN",
    "NativePixelClusterNNBaseline",
    "NativePixelClusterNNAvx2",
]:
    source = (
        A
        / f"athena-build-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool/CMakeFiles/SiClusterizationToolLib.dir/src/{name}.cxx.o"
    )
    target = out / (name + ".o")
    shutil.copy2(source, target)
    objects.append(str(target))
commands = json.loads((old / "commands.json").read_text())
compile = [t.replace(str(old), str(out)) for t in commands["compile"]]
compile.insert(compile.index("--") + 2, "-I" + str(native))
link = [t.replace(str(old), str(out)) for t in commands["link"]] + objects
(out / "commands.json").write_text(
    json.dumps(dict(compile=compile, link=link), indent=2)
)
print("Compiling native adapter", flush=True)
subprocess.run(compile, cwd=A / "athena-build-tail-score", check=True)
print("Linking unchanged native kernels", flush=True)
subprocess.run(link, cwd=A / "athena-build-tail-score", check=True)
files = [
    *map(Path, objects),
    out / "lib/libActsTrackReconstruction.so",
    p,
    src / "src/detail/NativeStudyNN.h",
]
(out / "sha256.json").write_text(
    json.dumps(
        {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2
    )
)
print("NATIVE ADAPTER READY", flush=True)
