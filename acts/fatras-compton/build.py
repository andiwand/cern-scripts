"""Compile Compton with the recorded ACTS ABI and accepted numerical navigator."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--build", type=Path, default=Path.home() / "cern/build/acts/acts/dev3")
p.add_argument(
    "--geant4-lib",
    type=Path,
    default=Path.home() / "cern/source/acts/ci-dependencies/.spack-env/view/lib",
)
a = p.parse_args()
tools = Path(__file__).resolve().parent.parent
bridge = a.work / "bridge"
subprocess.run(
    [
        sys.executable,
        str(tools / "fatras-soft-secondaries/build.py"),
        "--source",
        str(a.source),
        "--build",
        str(a.build),
        "--output",
        str(bridge),
        "--geant4-lib",
        str(a.geant4_lib),
        "--photon-cut",
        "0.0001",
        "--prepare-only",
    ],
    check=True,
)
h = bridge / "runtime-fatras.hpp"
h.write_text(
    h.read_text().replace(
        "double photonPMin = 0.0001;",
        "double photonPMin = 0.0001;\n    bool emComptonScattering = true;",
    )
)
s = bridge / "runtime-fatras.cpp"
text = s.read_text()
text = text.replace(
    "PYBIND11_MODULE(runtime_fatras,module) {",
    """namespace { double photonCut = .0001; bool comptonEnabled = true; }
PYBIND11_MODULE(runtime_fatras,module) {
 module.def("configure_photons",[](double cut, bool enabled) {
  if (!(cut >= 0) || !std::isfinite(cut)) throw std::invalid_argument("Invalid photon cut");
  photonCut=cut; comptonEnabled=enabled;
 });""",
)
text = text.replace(
    "  if(live) {",
    """  cfg.photonPMin=photonCut;
  cfg.emComptonScattering=comptonEnabled && (base.emPhotonConversion || base.emScattering || base.emEnergyLossIonisation || base.emEnergyLossRadiation);
  if(live) {""",
)
s.write_text(text)
record = json.loads((bridge / "module-build.json").read_text())
record["command"].insert(1, str(a.source / "Fatras/src/Physics/ComptonScattering.cpp"))
record["source_sha256"].update(
    {
        str(x): hashlib.sha256(x.read_bytes()).hexdigest()
        for x in [
            h,
            s,
            a.source / "Fatras/src/Physics/ComptonScattering.cpp",
            a.source
            / "Fatras/include/ActsFatras/Physics/ElectroMagnetic/ComptonScattering.hpp",
        ]
    }
)
(bridge / "module-build.json").write_text(json.dumps(record, indent=2))
subprocess.run(record["command"], check=True)
subprocess.run(
    [
        sys.executable,
        str(tools / "fatras-transport-performance/build.py"),
        "--source",
        str(a.source),
        "--bridge",
        str(bridge),
        "--output",
        str(a.work / "pruned-build"),
        "--variant",
        "cache",
        "--query-cache",
        "--surface-pruning",
    ],
    check=True,
)
