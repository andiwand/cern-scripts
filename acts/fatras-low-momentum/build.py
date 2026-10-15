"""Build a single-worker, fixed-geometry navigation experiment on live hadronics.
Uses the same compiler/ABI bridge as runtime validation; not a production plugin.
"""

from pathlib import Path
import argparse, subprocess, json, hashlib, shlex

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
p.add_argument("--bridge", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
root = Path(__file__).parent
s = (
    (a.source / "Core/include/Acts/Propagator/TryAllNavigator.hpp")
    .read_text()
    .replace("TryAllNavigator", "BoundedNavigator")
)
s = s.replace(
    "namespace Acts::Experimental {",
    '#include "spatial-index.hpp"\n\nnamespace Acts::Experimental {',
    1,
)
s = s.replace(
    "  Config m_cfg;",
    "  Config m_cfg;\n  mutable std::unordered_map<const TrackingVolume*, CandidateIndex> indexes;",
)
s = s.replace(
    "    // Find intersections with all candidates\n    for (const auto& candidate : state.navigationCandidates) {",
    """    auto it=indexes.find(state.currentVolume);
    if(it==indexes.end())it=indexes.try_emplace(state.currentVolume,state.navigationCandidates,state.options.geoContext).first;
    const auto selected=it->second.candidates(position,direction,nearLimit,farLimit,state.options.surfaceTolerance);
    for (const auto index : selected) {
      const auto& candidate=state.navigationCandidates[index];""",
)
(a.output / "bounded-navigator.hpp").write_text(s)
# Reuse the current live-backend bridge rather than link an old algorithm ABI.
h = (
    (a.bridge / "runtime-fatras.hpp")
    .read_text()
    .replace(
        "    std::shared_ptr<const ActsFatras::NuclearInteractionModel> nuclearInteractionModel;",
        """    std::shared_ptr<const ActsFatras::NuclearInteractionModel> nuclearInteractionModel;
    int navigationMode=0;
    double tryAllPtMax=0.5, tryAllFarLimit=5, tryAllStepMax=5, chargedLoopFraction=4;
    unsigned chargedMaxSteps=5000;""",
    )
)
(a.output / "runtime-fatras.hpp").write_text(h)
(a.output / "base-fatras.hpp").write_text((a.bridge / "base-fatras.hpp").read_text())
s = (a.bridge / "runtime-fatras.cpp").read_text()
s = s.replace(
    "namespace ActsExamples {",
    '#include "audit-propagator.hpp"\nnamespace ActsExamples {',
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
    "bool live) {",
    "bool live,int mode,double ptMax,double step,double loops,unsigned maxSteps) {",
)
s = s.replace(
    "  if(live) {",
    "  cfg.navigationMode=mode;cfg.tryAllPtMax=ptMax;cfg.tryAllFarLimit=step;cfg.tryAllStepMax=step;cfg.chargedLoopFraction=loops;cfg.chargedMaxSteps=maxSteps;\n  if(live) {",
)
pos = s.rfind("\n}")
s = s[:pos] + """
 module.def("statistics",[] {
   py::dict d;d["queries"]=spatialStats.queries;d["available"]=spatialStats.available;d["tested"]=spatialStats.tested;d["nodes"]=spatialStats.nodes;d["indexes"]=spatialStats.indexes;
   d["calls"]=navigationStats.calls;d["failures"]=navigationStats.failures;d["steps"]=navigationStats.steps;d["path_mm"]=navigationStats.path;d["transport_seconds"]=navigationStats.seconds;
   return d;
 });
""" + s[pos:]
(a.output / "runtime-fatras.cpp").write_text(s)
cmd = json.loads((a.bridge / "module-build.json").read_text())["command"]
old_source = Path(
    next(
        x for x in cmd if x.endswith("/Fatras/Geant4/src/Geant4NuclearInteraction.cpp")
    )
).parents[3]
cmd = [
    x.replace(str(old_source), str(a.source)).replace(str(a.bridge), str(a.output))
    for x in cmd
]
cmd[1:1] = ["-I" + str(root)]
(a.output / "build.json").write_text(
    json.dumps(
        {
            "command": cmd,
            "source_sha256": {
                str(x): hashlib.sha256(x.read_bytes()).hexdigest()
                for x in [
                    a.output / "runtime-fatras.cpp",
                    a.output / "bounded-navigator.hpp",
                    root / "spatial-index.hpp",
                    root / "audit-propagator.hpp",
                ]
            },
        },
        indent=2,
    )
)
subprocess.run(cmd, check=True)
