"""Build current radiation physics with the established frozen validation ABI."""

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
t = h.read_text()
needle = "double photonPMin = 0.0001;"
assert t.count(needle) == 1
t = t.replace(
    needle,
    needle
    + "\n    bool emComptonScattering = true;\n    bool emPositronAnnihilation = true;\n    double emBremsstrahlungPhotonMinEnergy = .0001;",
)
h.write_text(t)
s = bridge / "runtime-fatras.cpp"
t = s.read_text()
needle = "PYBIND11_MODULE(runtime_fatras,module) {"
assert t.count(needle) == 1
t = t.replace(
    needle,
    'namespace { double photonCut=.0001, radiationCut=.0001; bool comptonEnabled=true, annihilationEnabled=true; }\nPYBIND11_MODULE(runtime_fatras,module) {\n module.def("configure_annihilation",[](bool enabled) { annihilationEnabled=enabled; });\n module.def("configure_photons",[](double cut,bool enabled) {\n  if (!(cut>=0) || !std::isfinite(cut)) throw std::invalid_argument("Invalid photon cut");\n  photonCut=cut;comptonEnabled=enabled;\n });\n module.def("configure_radiation",[](double cut) {\n  if (!(cut>0)) throw std::invalid_argument("Invalid radiation cut");\n  radiationCut=cut;\n });',
)
needle = "  if(live) {"
assert t.count(needle) == 1
t = t.replace(
    needle,
    "  cfg.photonPMin=photonCut;\n  cfg.emComptonScattering=comptonEnabled && (base.emPhotonConversion || base.emScattering || base.emEnergyLossIonisation || base.emEnergyLossRadiation);\n  cfg.emPositronAnnihilation=annihilationEnabled && (base.emPhotonConversion || base.emScattering || base.emEnergyLossIonisation || base.emEnergyLossRadiation);\n  cfg.emBremsstrahlungPhotonMinEnergy=radiationCut;\n  if(live) {",
)
s.write_text(t)
record = json.loads((bridge / "module-build.json").read_text())
record["command"][1:1] = [
    str(a.source / "Fatras/src/Physics" / name)
    for name in ["Bremsstrahlung.cpp", "BetheHeitler.cpp", "ComptonScattering.cpp"]
]
record["source_sha256"].update(
    {
        str(x): hashlib.sha256(x.read_bytes()).hexdigest()
        for x in [
            h,
            s,
            *a.source.glob("Fatras/include/ActsFatras/Physics/ElectroMagnetic/*.hpp"),
            *a.source.glob("Fatras/src/Physics/*.cpp"),
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
