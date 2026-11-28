#!/usr/bin/env python3
"""Build the runtime_fatras validation bridge against a frozen ACTS build.

Compiles the Fatras simulation algorithm and the changed Fatras physics from
SOURCE into a Python module (runtime_fatras.so) that links against an existing
ACTS build whose Examples ABI matches d25514208b. This is a fast iteration
harness for physics changes, not a replacement for a normal ACTS build.

Layers (all on by default, newest configuration):
  base        RuntimeFatras algorithm + on-demand Geant4 hadronic backend
  soft        explicit ionisation (--ion-cut), photon acceptance (--photon-cut),
              native decays (--legacy-decays: ca045e1435 decays for ablation)
  --em        compton: native Compton (configure_photons)
              radiation: + explicit bremsstrahlung and positron annihilation
              (configure_radiation, configure_annihilation)
  --navigator cache: single-worker, fixed-geometry bounded navigator with
              cached volume candidates (--no-query-cache, --no-surface-pruning)

Outputs WORK/bridge (standard navigation) and WORK/pruned-build (bounded
navigator); pass either to inclusive_run.py --module-dir.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import acts_compile
import paths

HERE = Path(__file__).resolve().parent
BASE_REVISION = "d25514208b"
LEGACY_DECAY_REVISION = "ca045e1435"
FIELD = "    std::shared_ptr<const ActsFatras::NuclearInteractionModel> nuclearInteractionModel;"


def replace(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True)


PYBIND = """
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

EM_ENABLED = "(base.emPhotonConversion || base.emScattering || base.emEnergyLossIonisation || base.emEnergyLossRadiation)"
EM_CONFIG = {
    "compton": (
        "\n    bool emComptonScattering = true;",
        """namespace { double photonCut = .0001; bool comptonEnabled = true; }
PYBIND11_MODULE(runtime_fatras,module) {
 module.def("configure_photons",[](double cut, bool enabled) {
  if (!(cut >= 0) || !std::isfinite(cut)) throw std::invalid_argument("Invalid photon cut");
  photonCut=cut; comptonEnabled=enabled;
 });""",
        f"""  cfg.photonPMin=photonCut;
  cfg.emComptonScattering=comptonEnabled && {EM_ENABLED};
  if(live) {{""",
        ["ComptonScattering.cpp"],
    ),
    "radiation": (
        "\n    bool emComptonScattering = true;\n    bool emPositronAnnihilation = true;\n    double emBremsstrahlungPhotonMinEnergy = .0001;",
        """namespace { double photonCut=.0001, radiationCut=.0001; bool comptonEnabled=true, annihilationEnabled=true; }
PYBIND11_MODULE(runtime_fatras,module) {
 module.def("configure_annihilation",[](bool enabled) { annihilationEnabled=enabled; });
 module.def("configure_photons",[](double cut,bool enabled) {
  if (!(cut>=0) || !std::isfinite(cut)) throw std::invalid_argument("Invalid photon cut");
  photonCut=cut;comptonEnabled=enabled;
 });
 module.def("configure_radiation",[](double cut) {
  if (!(cut>0)) throw std::invalid_argument("Invalid radiation cut");
  radiationCut=cut;
 });""",
        f"""  cfg.photonPMin=photonCut;
  cfg.emComptonScattering=comptonEnabled && {EM_ENABLED};
  cfg.emPositronAnnihilation=annihilationEnabled && {EM_ENABLED};
  cfg.emBremsstrahlungPhotonMinEnergy=radiationCut;
  if(live) {{""",
        ["Bremsstrahlung.cpp", "BetheHeitler.cpp", "ComptonScattering.cpp"],
    ),
}


def build_bridge(a, out):
    """Generate and compile WORK/bridge; return its compile command."""
    src = a.source
    out.mkdir(parents=True, exist_ok=True)
    header = "Examples/Algorithms/Fatras/include/ActsExamples/Fatras/FatrasSimulation.hpp"
    (out / "base-fatras.hpp").write_text(git(src, "show", f"{BASE_REVISION}:{header}"))
    h = (src / header).read_text().replace("FatrasSimulation", "RuntimeFatras")
    start = h.index("  struct Config {")
    end = h.index("\n  /// Construct the algorithm", start)
    h = (
        h[:start]
        + "  struct Config : ActsExamples::FatrasSimulation::Config {\n"
        + FIELD
        + "\n  };\n"
        + h[end:]
    )
    h = h.replace("#pragma once", '#pragma once\n#include "base-fatras.hpp"')
    s = (
        (src / "Examples/Algorithms/Fatras/src/FatrasSimulation.cpp")
        .read_text()
        .replace('"ActsExamples/Fatras/FatrasSimulation.hpp"', '"runtime-fatras.hpp"')
        .replace("FatrasSimulation", "RuntimeFatras")
    ) + PYBIND

    sources = []
    hashed = []
    flags, _ = acts_compile.compile_flags(a.build, "examples", source=src)
    if a.soft:
        cut = repr(a.ion_cut) if a.ion_cut != float("inf") else "std::numeric_limits<double>::infinity()"
        h = replace(
            h,
            FIELD,
            FIELD
            + f"\n    double emIonisationSecondaryMinEnergy = {cut};\n    double photonPMin = {a.photon_cut!r};",
        )
        decay = src / "Fatras/src/Physics/NativeDecay.cpp"
        if a.legacy_decays:
            override = out.parent / ("legacy-" + out.name)
            target = override / "ActsFatras/Physics/Decay/NativeDecay.hpp"
            target.parent.mkdir(parents=True, exist_ok=True)
            for dest, path in [
                (target, "Fatras/include/ActsFatras/Physics/Decay/NativeDecay.hpp"),
                (override / "NativeDecay.cpp", "Fatras/src/Physics/NativeDecay.cpp"),
            ]:
                dest.write_text(git(src, "show", f"{LEGACY_DECAY_REVISION}:{path}"))
            decay = override / "NativeDecay.cpp"
            flags[1:1] = ["-I" + str(override)]
        # Compile the changed out-of-line physics; never use installed symbols.
        sources += [src / "Fatras/src/Physics/Ionisation.cpp", decay]
    if a.em != "none":
        fields, module, configure, physics = EM_CONFIG[a.em]
        h = replace(h, f"    double photonPMin = {a.photon_cut!r};", f"    double photonPMin = {a.photon_cut!r};" + fields)
        s = replace(s, "PYBIND11_MODULE(runtime_fatras,module) {", module)
        s = replace(s, "  if(live) {", configure)
        sources = [src / "Fatras/src/Physics" / name for name in physics] + sources
        hashed += [
            *src.glob("Fatras/include/ActsFatras/Physics/ElectroMagnetic/*.hpp"),
            *src.glob("Fatras/src/Physics/*.cpp"),
        ]
    (out / "runtime-fatras.hpp").write_text(h)
    (out / "runtime-fatras.cpp").write_text(s)
    sources += [
        out / "runtime-fatras.cpp",
        src / "Fatras/Geant4/src/Geant4NuclearInteraction.cpp",
        src / "Fatras/src/Physics/StandardInteractions.cpp",
        src / "Examples/Algorithms/Geant4/src/FatrasNuclearInteraction.cpp",
    ]
    g = a.geant4_lib
    cmd = [
        *flags,
        "-I" + str(out),
        "-I" + str(src / "Examples/Algorithms/Geant4/include"),
        "-I" + str(src / "Fatras/Geant4/include"),
        "-isystem",
        str(g.parent / "include/Geant4"),
        *map(str, sources),
        "-shared",
        "-undefined",
        "dynamic_lookup",
        "-o",
        str(out / "runtime_fatras.so"),
        *acts_compile.acts_libraries(
            a.build,
            ["ActsExamplesGeant4", "ActsExamplesFatras", "ActsExamplesFramework", "ActsFatras", "ActsCore"],
        ),
        *acts_compile.geant4_libraries(g, clhep=True),
        "-Wl,-rpath," + str(a.build / "lib"),
        "-Wl,-rpath," + str(g),
    ]
    (out / "module-build.json").write_text(
        json.dumps(
            {
                "command": cmd,
                "revision": git(src, "rev-parse", "HEAD").strip(),
                "source_sha256": {str(p): sha(p) for p in [*sources, out / "runtime-fatras.hpp", *hashed]},
            },
            indent=2,
        )
    )
    (out / "soft-physics.json").write_text(
        json.dumps(
            {
                "ionisation_cut_GeV": (a.ion_cut if a.ion_cut != float("inf") else None) if a.soft else None,
                "photon_cut_GeV": a.photon_cut if a.soft else None,
                "legacy_decays": a.legacy_decays,
                "em": a.em,
                "source": str(src),
            },
            indent=2,
        )
    )
    subprocess.run(cmd, check=True)
    return cmd


def navigator_header(a):
    """TryAllNavigator copy with cached, pruned per-volume candidate lookup."""
    nav = (
        (a.source / "Core/include/Acts/Propagator/TryAllNavigator.hpp")
        .read_text()
        .replace("TryAllNavigator", "BoundedNavigator")
    )
    nav = nav.replace(
        "namespace Acts::Experimental {",
        '#include "spatial-index.hpp"\n\nnamespace Acts::Experimental {',
        1,
    )
    nav = replace(
        nav,
        "  Config m_cfg;",
        """  Config m_cfg;
  struct VolumeCandidates {
    std::vector<detail::NavigationObjectCandidate> candidates;
    CandidateIndex index;
    VolumeCandidates(std::vector<detail::NavigationObjectCandidate> c,
                     const GeometryContext& gctx)
        : candidates(std::move(c)), index(candidates, gctx) {}
  };
  // Feasibility scope: one worker, immutable geometry/context. State borrows
  // map entries; unordered_map rehash does not invalidate their references.
  mutable std::unordered_map<const TrackingVolume*, VolumeCandidates> indexes;""",
    )
    nav = replace(
        nav,
        "    std::vector<detail::NavigationObjectCandidate> navigationCandidates;",
        """    const VolumeCandidates* volumeCandidates = nullptr;
    std::vector<std::size_t> selectedCandidates;""",
    )
    # VolumeCandidates must be declared before the public State definition.
    begin = nav.index("  struct VolumeCandidates {")
    end = nav.index("  mutable std::unordered_map", begin)
    declaration = nav[begin:end]
    nav = nav[:begin] + nav[end:]
    nav = replace(nav, "class BoundedNavigator final {", "class BoundedNavigator final {\n" + declaration)
    nav = replace(nav, "    state.navigationCandidates.clear();", "    state.volumeCandidates = nullptr;")
    nav = replace(
        nav,
        """    emplaceAllVolumeCandidates(
        state.navigationCandidates, *volume, m_cfg.resolveSensitive,
        m_cfg.resolveMaterial, m_cfg.resolvePassive,
        m_cfg.boundaryToleranceSurfaceApproach, logger());""",
        """    auto it = indexes.find(volume);
    if (it == indexes.end()) {
      std::vector<detail::NavigationObjectCandidate> candidates;
      emplaceAllVolumeCandidates(candidates, *volume, m_cfg.resolveSensitive,
          m_cfg.resolveMaterial, m_cfg.resolvePassive,
          m_cfg.boundaryToleranceSurfaceApproach, logger());
      it = indexes.try_emplace(volume, std::move(candidates),
                               state.options.geoContext).first;
    }
    state.volumeCandidates = &it->second;""",
    )
    nav = replace(
        nav,
        "    // Find intersections with all candidates\n    for (const auto& candidate : state.navigationCandidates) {",
        """    const auto& volume = *state.volumeCandidates;
    volume.index.candidates(position, direction, nearLimit, farLimit,
                            state.options.surfaceTolerance, state.selectedCandidates);
    for (const auto index : state.selectedCandidates) {
      const auto& candidate = volume.candidates[index];""",
    )
    nav = replace(
        nav,
        """      state.activeTargetsBehind =
          resolveTargets(state, stepEnd, stepDirection, nearLimit, farLimit);""",
        """      resolveTargets(state, stepEnd, stepDirection, nearLimit, farLimit,
                     state.activeTargetsBehind);""",
    )
    nav = replace(
        nav,
        """    state.activeTargetsAhead =
        resolveTargets(state, position, direction, nearLimit, farLimit);""",
        """    resolveTargets(state, position, direction, nearLimit, farLimit,
                   state.activeTargetsAhead);""",
    )
    nav = replace(nav, "  std::vector<NavigationTarget> resolveTargets(State& state,", "  void resolveTargets(State& state,")
    nav = replace(
        nav,
        """                                               double farLimit) const {
    std::vector<NavigationTarget> targets;""",
        """                                               double farLimit,
                                               std::vector<NavigationTarget>& targets) const {
    targets.clear();""",
    )
    nav = replace(nav, "    return targets;", "    return;")
    if a.query_cache:
        nav = replace(
            nav,
            "    std::vector<std::size_t> selectedCandidates;",
            "    std::vector<std::size_t> selectedCandidates;\n    CandidateIndex::QueryCache queryCache;",
        )
        nav = replace(
            nav,
            "state.options.surfaceTolerance, state.selectedCandidates);",
            "state.options.surfaceTolerance, state.selectedCandidates, state.queryCache);",
        )
    if a.surface_pruning:
        nav = replace(nav, "index(candidates, gctx)", "index(candidates, gctx, true)")
    return nav


def build_navigator(a, bridge, out, bridge_cmd):
    """Generate and compile the bounded-navigator module from the bridge."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "bounded-navigator.hpp").write_text(navigator_header(a))
    for name in ["spatial-index.hpp", "audit-propagator.hpp"]:
        (out / name).write_text((HERE / "bridge" / name).read_text())
    (out / "base-fatras.hpp").write_text((bridge / "base-fatras.hpp").read_text())
    h = replace(
        (bridge / "runtime-fatras.hpp").read_text(),
        FIELD,
        FIELD
        + """
    int navigationMode=0;
    double tryAllPtMax=0.5, tryAllFarLimit=5, tryAllStepMax=5, chargedLoopFraction=4;
    unsigned chargedMaxSteps=5000;""",
    )
    (out / "runtime-fatras.hpp").write_text(h)
    s = (bridge / "runtime-fatras.cpp").read_text()
    s = s.replace("namespace ActsExamples {", '#include "audit-propagator.hpp"\nnamespace ActsExamples {', 1)
    s = replace(
        s,
        "using ChargedPropagator = Acts::Propagator<ChargedStepper, Acts::Navigator>;",
        "using ChargedPropagator = AuditPropagator;",
    )
    start = s.index("ChargedPropagator(ChargedStepper(cfg.magneticField),")
    end = s.index('\n                logger.clone("Simulation")),', start)
    s = s[:start] + 'ChargedPropagator(cfg, logger.clone("SimProp")),' + s[end:]
    s = replace(s, "bool live) {", "bool live,int mode,double ptMax,double step,double loops,unsigned maxSteps) {")
    s = replace(
        s,
        "  if(live) {",
        "  cfg.navigationMode=mode;cfg.tryAllPtMax=ptMax;cfg.tryAllFarLimit=step;cfg.tryAllStepMax=step;cfg.chargedLoopFraction=loops;cfg.chargedMaxSteps=maxSteps;\n  if(live) {",
    )
    pos = s.rfind("\n}")
    s = (
        s[:pos]
        + """
 module.def("statistics",[] {
   py::dict d;d["queries"]=spatialStats.queries;d["available"]=spatialStats.available;d["tested"]=spatialStats.tested;d["nodes"]=spatialStats.nodes;d["indexes"]=spatialStats.indexes;
   d["calls"]=navigationStats.calls;d["failures"]=navigationStats.failures;d["steps"]=navigationStats.steps;d["path_mm"]=navigationStats.path;d["transport_seconds"]=navigationStats.seconds;
   return d;
 });
"""
        + s[pos:]
    )
    (out / "runtime-fatras.cpp").write_text(s)
    cmd = [x.replace(str(bridge), str(out)) for x in bridge_cmd]
    cmd[1:1] = ["-I" + str(HERE / "bridge")]
    record = {
        "variant": "cache",
        "query_cache": a.query_cache,
        "surface_pruning": a.surface_pruning,
        "command": cmd,
        "source_sha256": {str(x): sha(x) for x in sorted(out.iterdir()) if x.suffix in (".hpp", ".cpp")},
    }
    (out / "experiment-build.json").write_text(json.dumps(record, indent=2))
    subprocess.run(cmd, check=True)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--source", type=Path, default=paths.SOURCE)
    p.add_argument("--build", type=Path, default=paths.BUILD)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--geant4-lib", type=Path, default=paths.GEANT4_LIB)
    p.add_argument("--no-soft", dest="soft", action="store_false", help="Base layer only")
    p.add_argument(
        "--ion-cut",
        type=float,
        default=0.0001,
        help="Electron kinetic production cut in GeV; inf keeps the legacy continuous loss",
    )
    p.add_argument("--photon-cut", type=float, default=0.0001, help="Photon acceptance in GeV")
    p.add_argument("--legacy-decays", action="store_true")
    p.add_argument("--em", choices=["none", "compton", "radiation"], default="radiation")
    p.add_argument("--navigator", choices=["none", "cache"], default="cache")
    p.add_argument("--no-query-cache", dest="query_cache", action="store_false")
    p.add_argument("--no-surface-pruning", dest="surface_pruning", action="store_false")
    a = p.parse_args()
    if not a.soft and (a.em != "none" or a.legacy_decays):
        p.error("--em and --legacy-decays need the soft layer")
    a.source, a.build, a.work = a.source.resolve(), a.build.resolve(), a.work.resolve()
    bridge = a.work / "bridge"
    cmd = build_bridge(a, bridge)
    if a.navigator == "cache":
        build_navigator(a, bridge, a.work / "pruned-build", cmd)


if __name__ == "__main__":
    main()
