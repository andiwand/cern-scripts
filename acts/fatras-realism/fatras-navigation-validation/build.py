#!/usr/bin/env python3
"""Build an external navigation experiment from a pinned Fatras algorithm."""

import argparse, json, shlex, subprocess, hashlib
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
root = Path(__file__).parent
header = (
    a.source
    / "Examples/Algorithms/Fatras/include/ActsExamples/Fatras/FatrasSimulation.hpp"
)
source = a.source / "Examples/Algorithms/Fatras/src/FatrasSimulation.cpp"
h = header.read_text().replace("FatrasSimulation", "NavigationFatras")
start = h.index("  struct Config {")
end = h.index("\n  /// Construct the algorithm", start)
h = h[:start] + """  struct Config : ActsExamples::FatrasSimulation::Config {
    double chargedPMin=0.1;
    double chargedPtMin=0.05;
    double tryAllPtMax=0;
    double tryAllFarLimit=10;
    double tryAllStepMax=10;
    double chargedLoopFraction=0.5;
    unsigned chargedMaxSteps=1000;
  };
""" + h[end:]
h = h.replace(
    "#pragma once", '#pragma once\n#include "ActsExamples/Fatras/FatrasSimulation.hpp"'
)
(a.output / "navigation-fatras.hpp").write_text(h)
s = (
    source.read_text()
    .replace('"ActsExamples/Fatras/FatrasSimulation.hpp"', '"navigation-fatras.hpp"')
    .replace("FatrasSimulation", "NavigationFatras")
)
s = s.replace(
    "namespace ActsExamples {",
    '#include "audit-propagator.hpp"\n\nnamespace ActsExamples {',
    1,
)
s = s.replace(
    "using ChargedPropagator = Acts::Propagator<ChargedStepper, Acts::Navigator>;",
    "using ChargedPropagator = AuditPropagator;",
)
start = s.index("ChargedPropagator(ChargedStepper(cfg.magneticField),")
end = s.index('\n                logger.clone("Simulation")),', start)
s = s[:start] + 'ChargedPropagator(cfg, logger.clone("SimProp")),' + s[end:]
s = s.replace(
    "simulation.selectCharged.get<CutPMin>().valMin = cfg.pMin;",
    "simulation.selectCharged.get<CutPMin>().valMin = cfg.chargedPMin;",
)
s = s.replace(
    "simulation.selectCharged.get<CutPtMin>().valMin = cfg.pTMin;",
    "simulation.selectCharged.get<CutPtMin>().valMin = cfg.chargedPtMin;",
)
s = s.replace(
    "cfg.pMin, std::move(nuclearTable)", "cfg.chargedPMin, std::move(nuclearTable)"
)
s += """
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py=pybind11;
PYBIND11_MODULE(navigation_fatras,module) {
  py::class_<ActsExamples::NavigationFatras,ActsExamples::IAlgorithm,std::shared_ptr<ActsExamples::NavigationFatras>>(module,"NavigationFatras")
    .def_property_readonly("config",[](const ActsExamples::NavigationFatras& sim) {
      return static_cast<ActsExamples::FatrasSimulation::Config>(sim.config());
    });
  module.def("make",[](const ActsExamples::FatrasSimulation::Config& base,
      double ptMax,double farLimit,double stepMax,double loopFraction,unsigned maxSteps, double pMin,double ptMin) {
    ActsExamples::NavigationFatras::Config cfg;
    static_cast<ActsExamples::FatrasSimulation::Config&>(cfg)=base;
    cfg.chargedPMin=pMin;cfg.chargedPtMin=ptMin;
    cfg.tryAllPtMax=ptMax;cfg.tryAllFarLimit=farLimit;cfg.tryAllStepMax=stepMax;
    cfg.chargedLoopFraction=loopFraction;cfg.chargedMaxSteps=maxSteps;
    return std::static_pointer_cast<ActsExamples::IAlgorithm>(
      std::make_shared<ActsExamples::NavigationFatras>(cfg,Acts::getDefaultLogger("NavigationFatras",Acts::Logging::INFO)));
  });
  module.def("statistics",[] {
    py::dict result;result["calls"]=navigationStats.calls;result["failures"]=navigationStats.failures;
    result["steps"]=navigationStats.steps;result["path_mm"]=navigationStats.path;
    return result;
  });
}
"""
(a.output / "navigation-fatras.cpp").write_text(s)
entries = json.loads((a.build / "compile_commands.json").read_text())
e = next(e for e in entries if e["file"].endswith("/ExampleAlgorithms.cpp"))
flags = shlex.split(e["command"])
args = []
i = 0
while i < len(flags):
    if flags[i] in ["-o", "-c"]:
        i += 2
        continue
    if flags[i] == "-g":
        i += 1
        continue
    args.append(flags[i])
    i += 1
libs = [
    str(a.build / "lib" / ("lib" + n + ".dylib"))
    for n in ["ActsExamplesFatras", "ActsExamplesFramework", "ActsFatras", "ActsCore"]
]
cmd = args + [
    "-I" + str(root),
    "-I" + str(a.output),
    str(a.output / "navigation-fatras.cpp"),
    "-shared",
    "-undefined",
    "dynamic_lookup",
    "-o",
    str(a.output / "navigation_fatras.so"),
    *libs,
    "-Wl,-rpath," + str(a.build / "lib"),
]
(a.output / "build-provenance.json").write_text(
    json.dumps(
        {
            "source_sha256": {
                str(x): hashlib.sha256(x.read_bytes()).hexdigest()
                for x in [header, source, root / "audit-propagator.hpp"]
            },
            "command": cmd,
        },
        indent=2,
    )
    + "\n"
)
subprocess.run(cmd, check=True, cwd=e["directory"])
