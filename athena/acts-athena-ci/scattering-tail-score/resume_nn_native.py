"""Retry adapter compilation after correcting the CMake wrapper argument position."""

import hashlib
import json
from pathlib import Path
import subprocess

A = Path("/home/astefl/source/acts/acts-athena-ci")
out = A / "run/scattering-tail-score/nn-native-control"
p = out / "commands.json"
c = json.loads(p.read_text())
assert c["compile"][1].startswith("-I")
include = c["compile"].pop(1)
c["compile"].insert(c["compile"].index("--") + 2, include)
p.write_text(json.dumps(c, indent=2))
for stage in ["compile", "link"]:
    print(stage, flush=True)
    subprocess.run(c[stage], cwd=A / "athena-build-tail-score", check=True)
files = [
    *out.glob("Native*.o"),
    out / "lib/libActsTrackReconstruction.so",
    out / "src/ActsTrackReconstruction/src/detail/NNClusterCalibratorToolImpl.icc",
    out / "src/ActsTrackReconstruction/src/detail/NativeStudyNN.h",
]
(out / "sha256.json").write_text(
    json.dumps(
        {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2
    )
)
print("NATIVE ADAPTER READY", flush=True)
