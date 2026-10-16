"""Compare the analytic kernel with the installed G4 model (run inside run-env.sh)."""

import argparse, json, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
w = p.parse_args().work
c = json.loads((w / "slab-build/build.json").read_text())
c = [x for x in c if not x.endswith(".cpp")]
c[c.index("-o") + 1] = str(w / "kernel")
c.append(str(Path(__file__).with_suffix(".cpp")))
(w / "kernel-build.json").write_text(json.dumps(c, indent=2))
with (w / "kernel-build.log").open("w") as f:
    subprocess.run(c, stdout=f, stderr=subprocess.STDOUT, check=True)
with (w / "kernel.csv").open("w") as f:
    subprocess.run([str(w / "kernel")], stdout=f, check=True)
