#!/usr/bin/env python3
"""Inclusive ODD simulation with matched output and CPU timing.

Modes:
  main     unmodified ACTS main (standard EM only); run with a main build
  changed  Fatras with native decays and a hadronic --table (local-L0 reference)
  live     Fatras with the on-demand Geant4 hadronic backend (no table)
  geant4   FTFP_BERT defaults in the physical ID world (id_world module);
           no extra time kill unless --geant4-time-max-ns

The script re-executes itself under run-env.sh, refuses to overwrite OUTPUT,
and writes OUTPUT.log, OUTPUT.command.json and OUTPUT/metadata.json.

With --module-dir (bridge_build.py output) Fatras runs through runtime_fatras:
--photon-cut-MeV/--disable-compton/--brems-cut-MeV/--disable-annihilation
configure the bridge EM physics, --navigation-mode etc. the bounded navigator
(one worker, fixed geometry). --soft selects the accepted soft-transport
settings: bounded navigation, 5 mm steps, 4 turns, 50000 steps,
p >= 0.2 MeV, pT >= 0.05 MeV.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

program_start = time.perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

SOFT = {
    "navigation_mode": 2,
    "navigation_step": 5.0,
    "max_steps": 50000,
    "loops": 4.0,
    "p_min": 0.0002,
    "pt_min": 0.00005,
}
# Fields configured inside the bridge; absent from the frozen Python Config.
BRIDGE_FIELDS = ("emComptonScattering", "emBremsstrahlungPhotonMinEnergy", "emPositronAnnihilation")

p = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
p.add_argument("--mode", choices=["main", "changed", "geant4", "live"], required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--source", type=Path, default=paths.SOURCE)
p.add_argument("--build", type=Path, default=paths.BUILD)
p.add_argument("--revision", help="Expected source revision (default: its HEAD)")
p.add_argument("--input", type=Path, default=paths.INPUTS)
p.add_argument("--material-map", type=Path, default=paths.MATERIAL_MAP)
p.add_argument("--table", type=Path)
p.add_argument("--events", type=int, default=3)
p.add_argument("--threads", type=int, default=1)
p.add_argument("--seed", type=int, default=42)
p.add_argument(
    "--geant4-time-max-ns",
    type=float,
    help="Optional explicit time kill; default leaves Geant4 physics-list transport unchanged",
)
p.add_argument(
    "--allow-prefiltered-input",
    action="store_true",
    help="Explicitly reproduce a historical momentum-filtered Geant4 sample",
)
p.add_argument("--world-module", type=Path, default=paths.ID_WORLD, help="Directory with id_world.so")
p.add_argument("--observer-module", type=Path, help="geant4: directory with gap_observer.so")
p.add_argument("--module-dir", type=Path, help="runtime_fatras bridge (bridge_build.py)")
bridge = p.add_argument_group("bridge EM physics")
bridge.add_argument("--photon-cut-MeV", type=float, default=0.1)
bridge.add_argument("--disable-compton", action="store_true")
bridge.add_argument("--brems-cut-MeV", type=float, default=0.1, help="inf: legacy radiation model")
bridge.add_argument("--disable-annihilation", action="store_true")
nav = p.add_argument_group("bounded navigation (pruned-build bridge)")
nav.add_argument("--soft", action="store_true", help="Accepted soft-transport settings")
nav.add_argument("--navigation-mode", type=int, choices=[0, 1, 2])
nav.add_argument("--navigation-pt-max", type=float, default=0.5, help="GeV")
nav.add_argument("--navigation-step", type=float, help="mm (default 5)")
nav.add_argument("--loops", type=float, help="default 4")
nav.add_argument("--max-steps", type=int, help="default 5000")
nav.add_argument("--p-min", type=float, help="GeV (default 0.02)")
nav.add_argument("--pt-min", type=float, help="GeV (default 0.005)")
nav.add_argument("--transport-only", action="store_true")
a = p.parse_args()
if a.soft:
    for key, value in SOFT.items():
        if getattr(a, key) is None:
            setattr(a, key, value)
bounded = a.navigation_mode is not None
for key, value in dict(navigation_step=5.0, loops=4.0, max_steps=5000, p_min=0.02, pt_min=0.005).items():
    if getattr(a, key) is None:
        setattr(a, key, value)
if a.threads < 1 or (a.mode == "geant4" and a.threads != 1):
    p.error("positive worker count required; the Geant4 reference uses one worker")
if a.mode == "live" and a.table is not None:
    p.error("On-demand mode must not be supplied a custom table")
if a.mode == "changed" and a.table is None:
    p.error("--table is required for changed Fatras")
if bounded and (a.mode != "live" or not a.module_dir or a.threads != 1):
    p.error("bounded navigation requires live mode, --module-dir and one worker")
if min(a.navigation_step, a.loops, a.max_steps) <= 0 or min(a.navigation_pt_max, a.p_min, a.pt_min) < 0:
    p.error("invalid transport settings")
if a.observer_module and a.mode != "geant4":
    p.error("--observer-module is a Geant4 diagnostic")
if a.geant4_time_max_ns is not None and a.geant4_time_max_ns <= 0:
    p.error("Explicit Geant4 time limit must be positive")

if os.environ.get("FATRAS_INSIDE_ENV") != "1":
    if a.output.exists():
        p.error("Refusing to overwrite output")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(paths.RUN_ENV), str(Path(__file__).resolve()), *sys.argv[1:]]
    a.output.with_suffix(".command.json").write_text(json.dumps(command, indent=2))
    env = dict(os.environ, FATRAS_INSIDE_ENV="1", ACTS_VALIDATION_BUILD=str(a.build))
    with a.output.with_suffix(".log").open("w") as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(a.output)
    sys.exit()

import importlib.util
import resource

import acts
import acts.examples
import acts.root
from acts.examples.odd import getOpenDataDetector

spec = importlib.util.spec_from_file_location(
    "acts.examples.simulation", a.source / "Python/Examples/python/simulation.py"
)
simulation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simulation)
addFatras, addGeant4 = simulation.addFatras, simulation.addGeant4
git = lambda *args: subprocess.check_output(["git", "-C", str(a.source), *args], text=True).strip()
revision = git("rev-parse", a.revision or "HEAD")
if git("rev-parse", "HEAD") != revision:
    p.error("Checkout does not match the requested revision")
binding = sys.modules["acts.ActsPythonBindings"].__file__
if not Path(binding).resolve().is_relative_to(a.build.resolve()):
    p.error("Activate the specified build before running")
selection_path = a.input / "selection.json"
selection = json.loads(selection_path.read_text()) if selection_path.exists() else None
if a.mode == "geant4" and selection and not a.allow_prefiltered_input:
    if (selection.get("p_min_GeV") or 0) > 0 or (selection.get("pt_min_GeV") or 0) > 0:
        p.error("Inclusive Geant4 reference requires input without momentum filtering")
a.output.mkdir(parents=True, exist_ok=False)
u = acts.UnitConstants
level = acts.logging.INFO
s = acts.examples.Sequencer(
    events=a.events,
    numThreads=a.threads,
    logLevel=level,
    outputDir=str(a.output),
    trackFpes=False,
)
s.addReader(
    acts.examples.CsvParticleReader(
        level=level,
        inputDir=str(a.input),
        inputStem="particles",
        outputParticles="particles_generated",
    )
)
material = acts.root.RootMaterialDecorator(
    fileName=str(a.material_map),
    level=acts.logging.WARNING,
)
detector = getOpenDataDetector(
    materialDecorator=material,
    buildCalorimeter=False,
    buildMuonSystem=False,
    logLevel=acts.logging.WARNING,
)
geometry = detector.trackingGeometry()
for decorator in detector.contextDecorators():
    s.addContextDecorator(decorator)
field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))
rnd = acts.examples.RandomNumbers(seed=a.seed)
world_report = None
runtime_fatras = None
bridge_physics = None
if a.mode == "geant4":
    addGeant4(
        s,
        detector,
        geometry,
        field,
        rnd,
        inputParticles="particles_generated",
        outputDirCsv=a.output,
        recordHitsOfSecondaries=True,
        keepParticlesWithoutHits=True,
        killSecondaries=False,
        killVolume=geometry.highestTrackingVolume,
        physicsList="FTFP_BERT",
        **(
            {"killAfterTime": a.geant4_time_max_ns * u.ns}
            if a.geant4_time_max_ns is not None
            else {}
        ),
    )
    sys.path.insert(0, str(a.world_module))
    import id_world

    bounds = geometry.highestTrackingVolume.volumeBounds.values()
    assert bounds[0] == 0 and abs(bounds[3] - 3.141592653589793) < 1e-12
    world_report = id_world.confine(bounds[1], bounds[2])
    if a.observer_module:
        sys.path.insert(0, str(a.observer_module))
        import gap_observer

        gap_observer.install(str(a.output / "observer.tsv"))
else:
    changed = (
        dict(
            pTMin=0.05 * u.GeV,
            enableDecays=True,
            enableNeutralHadronInteractions=True,
            neutralHadronKineticEnergyMin=0.01 * u.GeV,
            neutralHadronTimeMax=1000 * u.ns,
            nuclearInteractionUseReferenceMaterial=True,
            nuclearInteractionTable=str(a.table) if a.table else "",
        )
        if a.mode in ["changed", "live"]
        else {}
    )
    if a.module_dir and a.mode in ["changed", "live"]:
        sys.path.insert(0, str(a.module_dir))
        import runtime_fatras

        bridge_physics = {}
        if hasattr(runtime_fatras, "configure_annihilation"):
            runtime_fatras.configure_annihilation(not a.disable_annihilation)
            bridge_physics["positron_annihilation"] = not a.disable_annihilation
        if hasattr(runtime_fatras, "configure_photons"):
            runtime_fatras.configure_photons(a.photon_cut_MeV * 0.001, not a.disable_compton)
            bridge_physics["photon_cut_GeV"] = a.photon_cut_MeV * 0.001
            bridge_physics["compton"] = not a.disable_compton
        if hasattr(runtime_fatras, "configure_radiation"):
            runtime_fatras.configure_radiation(a.brems_cut_MeV * 0.001)
            finite = a.brems_cut_MeV != float("inf")
            bridge_physics["brems_production_cut_GeV"] = a.brems_cut_MeV * 0.001 if finite else None
            bridge_physics["coupled_electron_losses"] = finite
        original = acts.examples.FatrasSimulation

        def factory(**kwargs):
            cfg = original.Config()
            for key, value in kwargs.items():
                if key != "level" and key not in BRIDGE_FIELDS:
                    setattr(cfg, key, value)
            live = a.mode == "live"
            if not bounded:
                return runtime_fatras.make(cfg, live)
            cfg.pMin = a.p_min
            cfg.pTMin = a.pt_min
            if a.transport_only:
                cfg.enableDecays = False
                cfg.emScattering = False
                cfg.emEnergyLossIonisation = False
                cfg.emEnergyLossRadiation = False
                cfg.emPhotonConversion = False
            return runtime_fatras.make(
                cfg,
                live and not a.transport_only,
                a.navigation_mode,
                a.navigation_pt_max,
                a.navigation_step,
                a.loops,
                a.max_steps,
            )

        acts.examples.FatrasSimulation = factory
    if a.mode == "live" and not a.module_dir:
        from acts.examples.geant4 import makeFatrasNuclearInteraction

        changed["nuclearInteractionModel"] = makeFatrasNuclearInteraction()
    addFatras(
        s,
        geometry,
        field,
        rnd,
        inputParticles="particles_generated",
        outputDirCsv=a.output,
        pMin=0.1 * u.GeV,
        enableInteractions=True,
        **changed,
    )
odd = Path(os.environ["ODD_PATH"])
metadata = {
    "mode": "fatras-main" if a.mode == "main" else a.mode,
    "baseline_ref": revision,
    "events": a.events,
    "seed": a.seed,
    "pileup": 200,
    "acts_revision": git("rev-parse", "HEAD"),
    "acts_worktree_dirty": bool(git("status", "--porcelain")),
    "source": str(a.source.resolve()),
    "build": str(a.build.resolve()),
    "python_module": acts.__file__,
    "native_module": binding,
    "table": str(a.table) if a.table else None,
    "table_sha256": (hashlib.sha256(a.table.read_bytes()).hexdigest() if a.table else None),
    "input": str(a.input.resolve()),
    "input_selection": selection,
    "geant4_explicit_time_max_ns": a.geant4_time_max_ns if a.mode == "geant4" else None,
    "p_min_GeV": 0.1 if a.mode != "geant4" else None,
    "pt_min_GeV": 0.05 if a.mode in ["changed", "live"] else None,
    "analysis_hit_p_min_GeV": None,
    "analysis_hit_pt_min_GeV": None,
    "physics": {
        "main": "Unmodified main: standard EM; no decays or hadronic interactions",
        "changed": "Standard EM; native decays; supplied hadronic table; local-L0 reference material",
        "live": "Native Fatras transport/EM/decays; on-demand FTFP_BERT inelastic final states, Si reference with local L0; no custom event library",
        "geant4": "FTFP_BERT defaults; charged primary and secondary hits; explicit time kill="
        + str(a.geant4_time_max_ns)
        + " ns",
    }[a.mode],
    "diagnostics": "None; standard CSV hit and particle writers in all modes",
    "num_threads": a.threads,
    "validation_bridge": str(a.module_dir) if a.module_dir else None,
    "geant4_dataset_environment": {
        k: v for k, v in os.environ.items() if k.startswith("G4") and k.endswith("DATA")
    },
    "transport_difference": "Main has no pTMin option or neutral decay exemptions",
    "field_T": [0, 0, 2],
    "odd_path": str(odd),
    "odd_revision": subprocess.check_output(
        ["git", "-C", str(odd), "rev-parse", "HEAD"], text=True
    ).strip(),
    "material_map": str(a.material_map.resolve()),
    "material_map_sha256": hashlib.sha256(a.material_map.read_bytes()).hexdigest(),
    "world_bounds": geometry.highestTrackingVolume.volumeBounds.values(),
    "geometry": "ODD tracker only (pixels + strips); no calorimeter or muon system",
    "geant4_world": world_report,
}
if runtime_fatras is not None:
    module = a.module_dir
    soft = module / "soft-physics.json"
    metadata["soft_physics"] = {
        **(json.loads(soft.read_text()) if soft.exists() else {}),
        **bridge_physics,
    }
    metadata["module_sha256"] = hashlib.sha256((module / "runtime_fatras.so").read_bytes()).hexdigest()
    for record in ["experiment-build.json", "module-build.json"]:
        if (module / record).exists():
            metadata["bridge_build"] = json.loads((module / record).read_text())
            break
if bounded:
    metadata["p_min_GeV"] = a.p_min
    metadata["pt_min_GeV"] = a.pt_min
    metadata["navigation"] = {
        "mode": a.navigation_mode,
        "pt_max_GeV": a.navigation_pt_max,
        "step_mm": a.navigation_step,
        "loops": a.loops,
        "max_steps": a.max_steps,
        "transport_only": a.transport_only,
    }
    if a.transport_only:
        metadata["physics"] = "Transport only; no decays or material interactions"
        metadata["soft_physics"] = None
if (a.input / "probes.json").exists():
    metadata["pileup"] = None
    metadata["sample"] = "Controlled probes; see input/probes.json"
if a.observer_module:
    metadata["observer"] = {
        "module": str(a.observer_module / "gap_observer.so"),
        "scope": "Read-only callback forwarding; output observer.tsv",
    }
meta_path = a.output / "metadata.json"
meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
start = time.perf_counter()
cpu_start = resource.getrusage(resource.RUSAGE_SELF)
metadata["setup_wall_seconds"] = start - program_start
metadata["setup_cpu_seconds"] = cpu_start.ru_utime + cpu_start.ru_stime
s.run()
metadata["sequencer_seconds"] = time.perf_counter() - start
cpu_end = resource.getrusage(resource.RUSAGE_SELF)
metadata["sequencer_user_seconds"] = cpu_end.ru_utime - cpu_start.ru_utime
metadata["sequencer_system_seconds"] = cpu_end.ru_stime - cpu_start.ru_stime
metadata["sequencer_cpu_seconds"] = (
    metadata["sequencer_user_seconds"] + metadata["sequencer_system_seconds"]
)
metadata["process_cpu_seconds"] = cpu_end.ru_utime + cpu_end.ru_stime
metadata["process_wall_seconds"] = time.perf_counter() - program_start
metadata["max_rss_MiB"] = cpu_end.ru_maxrss / (1024**2 if sys.platform == "darwin" else 1024)
metadata["cpu_scope"] = (
    "Process user+system time; setup includes imports/geometry/table; sequencer includes initialization, simulation, CSV I/O and finalization"
)
if bounded:
    metadata["navigation"]["statistics"] = dict(runtime_fatras.statistics())
if a.observer_module:
    gap_observer.flush()
meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
