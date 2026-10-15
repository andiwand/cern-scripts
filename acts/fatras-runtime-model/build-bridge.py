import json, shlex, subprocess, hashlib
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(
    description="Build the macOS validation bridge against a d25514208b Fatras build; not a replacement for a normal ACTS build."
)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--build", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--geant4-lib", type=Path, required=True)
a = parser.parse_args()
r = a.source
w = a.output
b = a.build
g = a.geant4_lib
w.mkdir(parents=True, exist_ok=True)
old = next(
    line.split("=", 1)[1]
    for line in (b / "CMakeCache.txt").read_text().splitlines()
    if line.startswith("CMAKE_HOME_DIRECTORY:")
)

header = "Examples/Algorithms/Fatras/include/ActsExamples/Fatras/FatrasSimulation.hpp"
base = subprocess.check_output(
    ["git", "-C", str(r), "show", "d25514208b:" + header], text=True
)
(w / "base-fatras.hpp").write_text(base)
h = (r / header).read_text().replace("FatrasSimulation", "RuntimeFatras")
start = h.index("  struct Config {")
end = h.index("\n  /// Construct the algorithm", start)
h = h[:start] + """  struct Config : ActsExamples::FatrasSimulation::Config {
    std::shared_ptr<const ActsFatras::NuclearInteractionModel> nuclearInteractionModel;
  };
""" + h[end:]
h = h.replace("#pragma once", '#pragma once\n#include "base-fatras.hpp"')
(w / "runtime-fatras.hpp").write_text(h)
s = (
    (r / "Examples/Algorithms/Fatras/src/FatrasSimulation.cpp")
    .read_text()
    .replace('"ActsExamples/Fatras/FatrasSimulation.hpp"', '"runtime-fatras.hpp"')
    .replace("FatrasSimulation", "RuntimeFatras")
)
s += """
#include "ActsFatras/Geant4/Geant4NuclearInteraction.hpp"
#include "ActsExamples/Geant4/FatrasNuclearInteraction.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py=pybind11;
PYBIND11_MODULE(runtime_fatras,module) {
 py::class_<ActsExamples::RuntimeFatras,ActsExamples::IAlgorithm,std::shared_ptr<ActsExamples::RuntimeFatras>>(module,"RuntimeFatras")
 .def_property_readonly("config",[](const ActsExamples::RuntimeFatras& sim) { return static_cast<ActsExamples::FatrasSimulation::Config>(sim.config()); });
 module.def("make",[](const ActsExamples::FatrasSimulation::Config& base,bool live) {
  ActsExamples::RuntimeFatras::Config cfg;
  static_cast<ActsExamples::FatrasSimulation::Config&>(cfg)=base;
  if(live) {
   cfg.nuclearInteractionModel=ActsExamples::makeFatrasNuclearInteraction();
  }
  return std::static_pointer_cast<ActsExamples::IAlgorithm>(std::make_shared<ActsExamples::RuntimeFatras>(cfg,Acts::getDefaultLogger("RuntimeFatras",Acts::Logging::INFO)));
 });
}
"""
(w / "runtime-fatras.cpp").write_text(s)
e = next(
    x
    for x in json.loads((b / "compile_commands.json").read_text())
    if x["file"].endswith("/ExampleAlgorithms.cpp")
)
f = shlex.split(e["command"])
args = []
i = 0
while i < len(f):
    if f[i] in ["-o", "-c"]:
        i += 2
        continue
    if f[i] == "-g":
        i += 1
        continue
    args.append(f[i].replace(old, str(r)))
    i += 1
args += [
    "-I" + str(w),
    "-I" + str(r / "Examples/Algorithms/Geant4/include"),
    "-I" + str(r / "Fatras/Geant4/include"),
    "-isystem",
    str(g.parent / "include/Geant4"),
]
sources = [
    w / "runtime-fatras.cpp",
    r / "Fatras/Geant4/src/Geant4NuclearInteraction.cpp",
    r / "Fatras/src/Physics/StandardInteractions.cpp",
    r / "Examples/Algorithms/Geant4/src/FatrasNuclearInteraction.cpp",
]
libs = (
    [
        str(b / "lib" / ("lib" + n + ".dylib"))
        for n in [
            "ActsExamplesGeant4",
            "ActsExamplesFatras",
            "ActsExamplesFramework",
            "ActsFatras",
            "ActsCore",
        ]
    ]
    + [str(x) for x in g.glob("libG4*.dylib")]
    + [str(g / "libCLHEP.dylib")]
)
cmd = (
    args
    + list(map(str, sources))
    + ["-shared", "-undefined", "dynamic_lookup", "-o", str(w / "runtime_fatras.so")]
    + libs
    + ["-Wl,-rpath," + str(b / "lib"), "-Wl,-rpath," + str(g)]
)
(w / "module-build.json").write_text(
    json.dumps(
        {
            "command": cmd,
            "revision": subprocess.check_output(
                ["git", "-C", str(r), "rev-parse", "HEAD"], text=True
            ).strip(),
            "source_sha256": {
                str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources
            },
        },
        indent=2,
    )
)
subprocess.run(cmd, check=True)
