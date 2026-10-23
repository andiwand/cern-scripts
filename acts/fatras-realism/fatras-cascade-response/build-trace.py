import argparse

p = argparse.ArgumentParser(
    description="Single-worker observational Compton-column build; changes no random draws"
)
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
p.add_argument("--source", type=__import__("pathlib").Path, required=True)
p.add_argument("--module", type=__import__("pathlib").Path, required=True)
a = p.parse_args()
from pathlib import Path
import shutil, json, subprocess

w = a.work
s = a.source
out = w / "trace-build"
out.mkdir(exist_ok=True)
old = a.module
for f in old.iterdir():
    if f.suffix in [".hpp", ".cpp"]:
        shutil.copy2(f, out / f.name)
h = out / "include/ActsFatras/Physics/ElectroMagnetic/ComptonScattering.hpp"
h.parent.mkdir(parents=True, exist_ok=True)
t = (
    (s / "Fatras/include/ActsFatras/Physics/ElectroMagnetic/ComptonScattering.hpp")
    .read_text()
    .replace(
        "#include <vector>",
        "#include <vector>\n#include <fstream>\n#include <cstdlib>\n#include <iomanip>",
    )
)
needle = "    if (uniform(generator) >= -std::expm1(-depth)) {\n      return false;\n    }\n    return scatter(generator, particle, generated);"
assert needle in t
t = t.replace(
    needle,
    """    const bool accepted = uniform(generator) < -std::expm1(-depth);
    const double energy = particle.energy();
    const auto id = particle.particleId();
    const auto start = generated.size();
    const bool answer = accepted && scatter(generator, particle, generated);
    static std::ofstream trace(std::getenv("FATRAS_COMPTON_TRACE"));
    trace << std::setprecision(12);
    for(auto v : id.components()) trace << v << ',';
    trace << energy*1000 << ',' << depth << ',' << slab.thickness() << ',' << accepted << ','
          << (accepted ? generated[start].energy()-generated[start].mass():0)*1000 << ','
          << (accepted ? generated[start+1].energy():0)*1000 << '\\n';
    return answer;""",
)
# Barcode tuple API is toArray, verify below.
t = t.replace("id.components()", "id.asArray()")
h.write_text(t)
r = json.loads((old / "experiment-build.json").read_text())
cmd = [
    x.replace(str(old), str(out)).replace(
        str(Path.home() / "cern/source/acts/acts/fatras-soft"), str(s)
    )
    for x in r["command"]
]
cmd[1:1] = ["-I" + str(out / "include")]
r["command"] = cmd
(out / "experiment-build.json").write_text(json.dumps(r, indent=2))
subprocess.run(cmd, check=True)
