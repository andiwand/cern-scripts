#!/usr/bin/env python3
"""Generate identical inputs and compare Geant4 and Fatras in the ODD tracker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import acts
import acts.examples
from acts.examples.simulation import addPythia8, addFatras, addGeant4
from acts.examples.odd import getOpenDataDetector

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("mode", choices=["generate", "geant4", "fatras", "fatras-em"])
p.add_argument("--output", type=Path, required=True)
p.add_argument("--input", type=Path)
p.add_argument("--events", type=int, default=20)
p.add_argument("--pileup", type=int, default=200)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--table", type=Path)
p.add_argument("--reference-material", action="store_true")
p.add_argument("--p-min", type=float, default=0.1)
p.add_argument("--pt-min", type=float, default=0.05)
a = p.parse_args()
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
rnd = acts.examples.RandomNumbers(seed=a.seed)
meta = {
    "mode": a.mode,
    "events": a.events,
    "seed": a.seed,
    "pileup": a.pileup,
    "p_min_GeV": a.p_min,
    "pt_min_GeV": a.pt_min,
    "acts_revision": subprocess.check_output(
        [
            "git",
            "-C",
            os.environ.get(
                "ACTS_VALIDATION_SOURCE", "/Users/andreas/cern/source/acts/acts/dev3"
            ),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip(),
    "build": os.environ.get(
        "ACTS_VALIDATION_BUILD", "/Users/andreas/cern/build/acts/acts/dev3"
    ),
    "table": str(a.table) if a.table else None,
    "reference_material": a.reference_material,
    "table_sha256": (
        hashlib.sha256(a.table.read_bytes()).hexdigest() if a.table else None
    ),
    "input": str(a.input) if a.input else None,
}
if a.mode == "generate":
    settings = ["310:mayDecay = off", "3122:mayDecay = off"]
    addPythia8(
        s,
        rnd=rnd,
        npileup=a.pileup,
        hardProcess=["Top:gg2ttbar = on", "Top:qqbar2ttbar = on", *settings],
        pileupProcess=["SoftQCD:all = on", *settings],
        vtxGen=acts.examples.GaussianVertexGenerator(
            mean=acts.Vector4(0, 0, 0, 0),
            stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 0),
        ),
        outputDirCsv=a.output,
        logLevel=acts.logging.WARNING,
    )
    meta["generator"] = (
        "Pythia8 ttbar plus Poisson pileup; 14 TeV; K-short/Lambda left undecayed"
    )
else:
    if a.input is None:
        p.error("--input is required for simulation")
    s.addReader(
        acts.examples.CsvParticleReader(
            level=level,
            inputDir=str(a.input),
            inputStem="particles",
            outputParticles="particles_generated",
        )
    )
    detector = getOpenDataDetector(
        buildCalorimeter=False, buildMuonSystem=False, logLevel=acts.logging.WARNING
    )
    geometry = detector.trackingGeometry()
    for decorator in detector.contextDecorators():
        s.addContextDecorator(decorator)
    field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))
    meta["field_T"] = [0, 0, 2]
    odd = Path(os.environ["ODD_PATH"])
    meta["odd_path"] = str(odd)
    meta["odd_revision"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=odd, text=True
    ).strip()
    meta["material_map_sha256"] = hashlib.sha256(
        (odd / "data/odd-material-maps.root").read_bytes()
    ).hexdigest()
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
            killAfterTime=1000 * u.ns,
        )
        meta["physics"] = (
            "FTFP_BERT; charged primary and secondary hits; 1000 ns global time cut"
        )
    else:
        addFatras(
            s,
            geometry,
            field,
            rnd,
            inputParticles="particles_generated",
            outputDirCsv=a.output,
            pMin=a.p_min * u.GeV,
            pTMin=a.pt_min * u.GeV,
            enableDecays=a.mode == "fatras",
            nuclearInteractionUseReferenceMaterial=a.reference_material,
            nuclearInteractionTable=(
                str(a.table) if a.table and a.mode == "fatras" else None
            ),
        )
        meta["physics"] = "standard EM" + (
            "; native decays; supplied hadronic table; "
            + (
                "local-L0 reference material"
                if a.reference_material
                else "exact material matching"
            )
            if a.mode == "fatras"
            else ""
        )
    meta["world_bounds"] = geometry.highestTrackingVolume.volumeBounds.values()
    meta["geometry"] = (
        "ODD tracker only (pixels + strips); no calorimeter or muon system"
    )
(a.output / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
t0 = time.perf_counter()
s.run()
meta["sequencer_seconds"] = time.perf_counter() - t0
(a.output / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
