"""Build isolated cache/helix experiments against the frozen validation ABI."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--bridge", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--variant", choices=["baseline", "cache", "helix"], required=True)
p.add_argument("--max-angle", type=float, default=0.25)
p.add_argument("--query-cache", action="store_true")
p.add_argument("--surface-pruning", action="store_true")
p.add_argument("--tools-root", type=Path, default=Path.home() / "cern/scripts/acts")
a = p.parse_args()
if not 0 < a.max_angle <= 1:
    p.error("max-angle must be in (0,1] radians")
root = Path(__file__).resolve().parent


def replace(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)


# Reuse the established ABI bridge generator, but compile only after applying
# the selected experiment. Keep the original compiler flags and source list.
original = a.tools_root / "fatras-low-momentum/build.py"
script = replace(original.read_text(), "subprocess.run(cmd, check=True)", "pass")
sys.argv = [str(original), "--source", str(a.source), "--bridge", str(a.bridge), "--output", str(a.output)]
exec(compile(script, str(original), "exec"), {"__name__": "__main__", "__file__": str(original)})
nav = (a.output / "bounded-navigator.hpp").read_text()
audit = (a.tools_root / "fatras-low-momentum/audit-propagator.hpp").read_text()
cmd = json.loads((a.output / "build.json").read_text())["command"]
sources = []
if a.variant != "baseline":
    nav = replace(nav,
        "  mutable std::unordered_map<const TrackingVolume*, CandidateIndex> indexes;",
        """  struct VolumeCandidates {
    std::vector<detail::NavigationObjectCandidate> candidates;
    CandidateIndex index;
    VolumeCandidates(std::vector<detail::NavigationObjectCandidate> c,
                     const GeometryContext& gctx)
        : candidates(std::move(c)), index(candidates, gctx) {}
  };
  // Feasibility scope: one worker, immutable geometry/context. State borrows
  // map entries; unordered_map rehash does not invalidate their references.
  mutable std::unordered_map<const TrackingVolume*, VolumeCandidates> indexes;""")
    nav = replace(nav,
        "    std::vector<detail::NavigationObjectCandidate> navigationCandidates;",
        """    const VolumeCandidates* volumeCandidates = nullptr;
    std::vector<std::size_t> selectedCandidates;""")
    # VolumeCandidates must be declared before the public State definition.
    begin = nav.index("  struct VolumeCandidates {")
    end = nav.index("  mutable std::unordered_map", begin)
    declaration = nav[begin:end]
    nav = nav[:begin] + nav[end:]
    nav = replace(nav, "class BoundedNavigator final {", "class BoundedNavigator final {\n" + declaration)
    nav = replace(nav, "    state.navigationCandidates.clear();", "    state.volumeCandidates = nullptr;")
    nav = replace(nav,
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
    state.volumeCandidates = &it->second;""")
    nav = replace(nav,
        """    auto it=indexes.find(state.currentVolume);
    if(it==indexes.end())it=indexes.try_emplace(state.currentVolume,state.navigationCandidates,state.options.geoContext).first;
    const auto selected=it->second.candidates(position,direction,nearLimit,farLimit,state.options.surfaceTolerance);
    for (const auto index : selected) {
      const auto& candidate=state.navigationCandidates[index];""",
        """    const auto& volume = *state.volumeCandidates;
    volume.index.candidates(position, direction, nearLimit, farLimit,
                            state.options.surfaceTolerance, state.selectedCandidates);
    for (const auto index : state.selectedCandidates) {
      const auto& candidate = volume.candidates[index];""")
    nav = replace(nav,
        """      state.activeTargetsBehind =
          resolveTargets(state, stepEnd, stepDirection, nearLimit, farLimit);""",
        """      resolveTargets(state, stepEnd, stepDirection, nearLimit, farLimit,
                     state.activeTargetsBehind);""")
    nav = replace(nav,
        """    state.activeTargetsAhead =
        resolveTargets(state, position, direction, nearLimit, farLimit);""",
        """    resolveTargets(state, position, direction, nearLimit, farLimit,
                   state.activeTargetsAhead);""")
    nav = replace(nav, "  std::vector<NavigationTarget> resolveTargets(State& state,", "  void resolveTargets(State& state,")
    nav = replace(nav,
        """                                               double farLimit) const {
    std::vector<NavigationTarget> targets;""",
        """                                               double farLimit,
                                               std::vector<NavigationTarget>& targets) const {
    targets.clear();""")
    nav = replace(nav, "    return targets;", "    return;")
    (a.output / "spatial-index.hpp").write_text((root / "spatial-index.hpp").read_text())
    if a.query_cache:
        nav = replace(nav, "    std::vector<std::size_t> selectedCandidates;",
            "    std::vector<std::size_t> selectedCandidates;\n    CandidateIndex::QueryCache queryCache;")
        nav = replace(nav, "state.options.surfaceTolerance, state.selectedCandidates);",
            "state.options.surfaceTolerance, state.selectedCandidates, state.queryCache);")
    if a.surface_pruning:
        nav = replace(nav, "index(candidates, gctx)", "index(candidates, gctx, true)")

if a.variant == "helix":
    # Reuse ACTS's closed-form stepper. Bound the turn per step using the
    # CURRENT momentum, including after material interactions. Surface physics
    # remains in SimulationActor. This experiment requires vacuum volumes.
    h = (a.source / "Core/include/Acts/Propagator/HelixStepper.hpp").read_text().replace("HelixStepper", "LocalHelixStepper")
    cpp = (a.source / "Core/src/Propagator/HelixStepper.cpp").read_text().replace("HelixStepper", "LocalHelixStepper")
    cpp = cpp.replace('"Acts/Propagator/LocalHelixStepper.hpp"', '"local-helix-stepper.hpp"')
    cpp = replace(cpp, 'const IVolumeMaterial* /*material*/) const {',
        'const IVolumeMaterial* material) const {\n  if (material != nullptr) {\n    throw std::runtime_error("Local helix experiment requires vacuum volumes");\n  }')
    if "double maxStepAngle" in h:
        h = replace(h, "double maxStepAngle = std::numeric_limits<double>::infinity();",
                    f"double maxStepAngle = {a.max_angle!r};")
    else:
        cpp = replace(cpp, "  const double initialH = state.stepSize.value() * propDir;",
            f"""  const double transportLimit = std::min(state.options.maxStepSize,
          {a.max_angle!r} / std::max(std::sqrt(omega2), 1e-30));
      state.stepSize.setUser(transportLimit);
      // A negative navigator correction takes priority over the positive user
      // limit in ConstrainedStep. Bound accuracy too, so reverse corrections
      // cannot turn through many revolutions or overflow the analytic formula.
      state.stepSize.setAccuracy(std::min(state.stepSize.accuracy(), transportLimit));
      const double initialH = state.stepSize.value() * propDir;""")
    if "0.5 * std::abs(h)" not in cpp:
        cpp = replace(cpp, "  return h;", """  // A blind-step chord may cross a surface that the curved arc skirts.
      // Exact backward/forward helix steps can then form a two-cycle. Refine
      // after any reverse correction, so the next forward trial cannot simply
      // repeat the same chord. No path or particle is discarded.
      if (propDir != Direction::fromScalarZeroAsPositive(h)) {
        state.stepSize.setAccuracy(std::min(state.stepSize.accuracy(),
                                            0.5 * std::abs(h)));
      }
      return h;""")
    (a.output / "local-helix-stepper.hpp").write_text(h)
    (a.output / "local-helix-stepper.cpp").write_text(cpp)
    sources.append(str(a.output / "local-helix-stepper.cpp"))
    audit = '#include "local-helix-stepper.hpp"\n' + audit
    audit = replace(audit, "using Local = Acts::Propagator<Acts::SympyStepper,", "using Local = Acts::Propagator<Acts::LocalHelixStepper,")
    audit = replace(audit, "local(Acts::SympyStepper(cfg.magneticField),", "local(Acts::LocalHelixStepper(cfg.magneticField),")
    audit = replace(audit, "      trial.stepping = options.stepping;", "      trial.stepping.setPlainOptions(options.stepping);")

(a.output / "bounded-navigator.hpp").write_text(nav)
(a.output / "audit-propagator.hpp").write_text(audit)
cmd[1:1] = sources
record = {"variant": a.variant, "query_cache": a.query_cache, "surface_pruning": a.surface_pruning, "max_angle": a.max_angle if a.variant == "helix" else None, "command": cmd}
record["source_sha256"] = {str(x): hashlib.sha256(x.read_bytes()).hexdigest() for x in a.output.iterdir() if x.suffix in [".hpp", ".cpp"]}
(a.output / "experiment-build.json").write_text(json.dumps(record, indent=2))
subprocess.run(cmd, check=True)
