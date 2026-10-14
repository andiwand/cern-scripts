#!/usr/bin/env python3
"""Compare unmodified main, changed Fatras and Geant4 with matched output and CPU timing."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import resource
import sys

program_start = time.perf_counter()

import acts
import acts.examples
import acts.root
from acts.examples.odd import getOpenDataDetector
from acts.examples.simulation import addFatras, addGeant4

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--mode", choices=["main", "changed", "geant4"], required=True)
p.add_argument("--table", type=Path)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
p.add_argument(
    "--revision",
    required=True,
    help="Expected source revision (main commit for the baseline)",
)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--material-map", type=Path, required=True)
p.add_argument("--events", type=int, default=20)
p.add_argument("--seed", type=int, default=42)
p.add_argument(
    "--geant4-time-max-ns",
    type=float,
    default=None,
    help="Optional explicit time kill; default leaves Geant4 physics-list transport unchanged",
)
p.add_argument(
    "--allow-prefiltered-input",
    action="store_true",
    help="Explicitly reproduce a historical momentum-filtered Geant4 sample",
)
a = p.parse_args()
git = lambda *args: subprocess.check_output(
    ["git", "-C", str(a.source), *args], text=True
).strip()
if git("rev-parse", "HEAD") != git("rev-parse", a.revision):
    p.error("Checkout does not match the requested revision")
if git("status", "--porcelain"):
    p.error("Source checkout must be clean")
binding = sys.modules["acts.ActsPythonBindings"].__file__
if not Path(binding).resolve().is_relative_to(a.build.resolve()):
    p.error("Activate the specified build before running")
if a.mode == "changed" and a.table is None:
    p.error("--table is required for changed Fatras")
selection_path = a.input / "selection.json"
selection = json.loads(selection_path.read_text()) if selection_path.exists() else None
if a.mode == "geant4" and selection and not a.allow_prefiltered_input:
    if (selection.get("p_min_GeV") or 0) > 0 or (selection.get("pt_min_GeV") or 0) > 0:
        p.error("Inclusive Geant4 reference requires input without momentum filtering")
if a.geant4_time_max_ns is not None and a.geant4_time_max_ns <= 0:
    p.error("Explicit Geant4 time limit must be positive")
a.output.mkdir(parents=True, exist_ok=False)
u = acts.UnitConstants
level = acts.logging.INFO
s = acts.examples.Sequencer(
    events=a.events,
    numThreads=1,
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
    import id_world

    bounds = geometry.highestTrackingVolume.volumeBounds.values()
    assert bounds[0] == 0 and abs(bounds[3] - 3.141592653589793) < 1e-12
    world_report = id_world.confine(bounds[1], bounds[2])
else:
    changed = (
        dict(
            pTMin=0.05 * u.GeV,
            enableDecays=True,
            enableNeutralHadronInteractions=True,
            neutralHadronKineticEnergyMin=0.01 * u.GeV,
            neutralHadronTimeMax=1000 * u.ns,
            nuclearInteractionUseReferenceMaterial=True,
            nuclearInteractionTable=str(a.table),
        )
        if a.mode == "changed"
        else {}
    )
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
    "baseline_ref": a.revision,
    "events": a.events,
    "seed": a.seed,
    "pileup": 200,
    "acts_revision": git("rev-parse", "HEAD"),
    "acts_worktree_dirty": False,
    "source": str(a.source.resolve()),
    "build": str(a.build.resolve()),
    "python_module": acts.__file__,
    "native_module": binding,
    "table": str(a.table) if a.table else None,
    "table_sha256": (
        hashlib.sha256(a.table.read_bytes()).hexdigest() if a.table else None
    ),
    "input": str(a.input.resolve()),
    "input_selection": selection,
    "geant4_explicit_time_max_ns": a.geant4_time_max_ns if a.mode == "geant4" else None,
    "p_min_GeV": 0.1 if a.mode != "geant4" else None,
    "pt_min_GeV": 0.05 if a.mode == "changed" else None,
    "analysis_hit_p_min_GeV": None,
    "analysis_hit_pt_min_GeV": None,
    "physics": {
        "main": "Unmodified main: standard EM; no decays or hadronic interactions",
        "changed": "Standard EM; native decays; supplied hadronic table; local-L0 reference material",
        "geant4": "FTFP_BERT defaults; charged primary and secondary hits; explicit time kill="
        + str(a.geant4_time_max_ns)
        + " ns",
    }[a.mode],
    "diagnostics": "None; standard CSV hit and particle writers in all three modes",
    "num_threads": 1,
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
metadata["max_rss_MiB"] = cpu_end.ru_maxrss / (
    1024**2 if sys.platform == "darwin" else 1024
)
metadata["cpu_scope"] = (
    "Process user+system time; setup includes imports/geometry/table; sequencer includes initialization, simulation, CSV I/O and finalization"
)
meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
