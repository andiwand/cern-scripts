#!/usr/bin/env python3
"""ODD ttbar chain for the CKF scattering tail prototype.

Branch `proto-ckf-scattering-tail` in acts dev3: Fatras uses the general
mixture scattering, and the CKF has `scatteringTailMode`.

Modes: 0 none, 1 retry, 2 retry with miss branch, 3 select only, 4 mixture.
"""

import argparse
import os
import pathlib

import acts
import acts.examples
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addPythia8,
    addGenParticleSelection,
    addFatras,
    addDigitization,
    addDigiParticleSelection,
)
from acts.examples.reconstruction import (
    addSeeding,
    CkfConfig,
    addCKFTracks,
    TrackSelectorConfig,
    addAmbiguityResolution,
    AmbiguityResolutionConfig,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

u = acts.UnitConstants

p = argparse.ArgumentParser()
p.add_argument("--output", "-o", type=pathlib.Path, required=True)
p.add_argument("--events", "-n", type=int, default=50)
p.add_argument("--skip", type=int, default=0)
p.add_argument("--jobs", "-j", type=int, default=-1)
p.add_argument("--pu", type=int, default=200)
p.add_argument("--mode", type=int, default=0)
p.add_argument("--chi2", type=float, nargs=2, default=[15.0, 25.0])
p.add_argument(
    "--record-scatters", action="store_true", help="write the truth scatter CSVs"
)
p.add_argument("--no-writers", action="store_true", help="timing runs")
p.add_argument(
    "--truth-only", action="store_true", help="write the selected particles only"
)
p.add_argument(
    "--pythia-verbose",
    action="store_true",
    help="let the pile-up Pythia print its warnings (diagnostic)",
)
p.add_argument(
    "--dump-stages",
    action="store_true",
    help="write generator, selection, simulation and digi-selection outputs, then stop",
)
p.add_argument(
    "--seed-perf", action="store_true", help="per-particle seed matching (diagnostic)"
)
p.add_argument(
    "--loose-selection",
    action="store_true",
    help="no CKF track selection, to see what the selection removes (diagnostic)",
)
args = p.parse_args()

outputDir = args.output
outputDir.mkdir(parents=True, exist_ok=True)
if args.record_scatters:
    (outputDir / "scatters").mkdir(exist_ok=True)
    os.environ["PROTO_SCATTER_DIR"] = str(outputDir / "scatters")
else:
    os.environ.pop("PROTO_SCATTER_DIR", None)

actsDir = pathlib.Path("/Users/andreas/cern/source/acts/acts/dev3")
geoDir = getOpenDataDetectorDirectory()
oddMaterialDeco = acts.IMaterialDecorator.fromFile(
    geoDir / "data/odd-material-maps.root"
)
detector = getOpenDataDetector(odd_dir=geoDir, materialDecorator=oddMaterialDeco)
trackingGeometry = detector.trackingGeometry()
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

s = acts.examples.Sequencer(
    events=args.events,
    skip=args.skip,
    numThreads=args.jobs,
    outputDir=str(outputDir),
    trackFpes=False,
)

addPythia8(
    s,
    hardProcess=["Top:qqbar2ttbar=on"],
    npileup=args.pu,
    pileupProcess=(
        [
            "SoftQCD:all = on",
            "Print:quiet = off",
            "Init:showProcesses = off",
            "Init:showMultipartonInteractions = off",
            "Init:showChangedSettings = off",
            "Init:showChangedParticleData = off",
            "Next:numberCount = 0",
            "Next:numberShowInfo = 0",
            "Next:numberShowProcess = 0",
            "Next:numberShowEvent = 0",
        ]
        if args.pythia_verbose
        else ["SoftQCD:all = on"]
    ),
    vtxGen=acts.examples.GaussianVertexGenerator(
        mean=acts.Vector4(0, 0, 0, 0),
        stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns),
    ),
    rnd=rnd,
)
addGenParticleSelection(
    s,
    ParticleSelectorConfig(
        rho=(0.0, 24 * u.mm),
        absZ=(0.0, 1.0 * u.m),
        eta=(-3.0, 3.0),
        pt=(150 * u.MeV, None),
    ),
)
addFatras(s, trackingGeometry, field, enableInteractions=True, rnd=rnd)
addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=actsDir / "Examples/Configs/odd-digi-smearing-config.json",
    rnd=rnd,
)
addDigiParticleSelection(
    s,
    ParticleSelectorConfig(
        pt=(1.0 * u.GeV, None),
        eta=(-3.0, 3.0),
        measurements=(9, None),
        removeNeutral=True,
    ),
)
if args.dump_stages:
    from acts.examples.root import RootParticleWriter, RootSimHitWriter

    for coll in (
        "particles_generated",
        "particles_generated_selected",
        "particles_simulated",
        "particles_selected",
    ):
        s.addWriter(
            RootParticleWriter(
                level=acts.logging.INFO,
                inputParticles=coll,
                filePath=str(outputDir / f"{coll}.root"),
            )
        )
    s.addWriter(
        RootSimHitWriter(
            level=acts.logging.INFO,
            inputSimHits="simhits",
            filePath=str(outputDir / "simhits.root"),
        )
    )
    s.run()
    raise SystemExit(0)

if args.truth_only:
    from acts.examples.root import RootParticleWriter

    s.addWriter(
        RootParticleWriter(
            level=acts.logging.INFO,
            inputParticles="particles_selected",
            filePath=str(outputDir / "particles_selected.root"),
        )
    )
    s.run()
    raise SystemExit(0)

addSeeding(
    s,
    trackingGeometry,
    field,
    initialSigmas=[
        1 * u.mm,
        1 * u.mm,
        1 * u.degree,
        1 * u.degree,
        0 * u.e / u.GeV,
        1 * u.ns,
    ],
    initialSigmaQoverPt=0.1 * u.e / u.GeV,
    initialSigmaPtRel=0.1,
    initialVarInflation=[1.0] * 6,
    particleHypothesis=acts.ParticleHypothesis.muon,
    geoSelectionConfigFile=actsDir / "Examples/Configs/odd-seeding-config.json",
)

outRoot = None if args.no_writers else outputDir
if args.seed_perf:
    from acts.examples.root import RootPatternRecognitionPerformanceWriter

    s.addWriter(
        RootPatternRecognitionPerformanceWriter(
            level=acts.logging.INFO,
            inputTracks="seed-tracks",
            inputParticles="particles_selected",
            inputTrackParticleMatching="seed_particle_matching",
            inputParticleTrackMatching="particle_seed_matching",
            inputParticleMeasurementsMap="particle_measurements_map",
            label="seed",
            filePath=str(outputDir / "performance_seeding_details.root"),
            writeMatchingDetails=True,
        )
    )
addCKFTracks(
    s,
    trackingGeometry,
    field,
    (
        TrackSelectorConfig(nMeasurementsMin=3)
        if args.loose_selection
        else TrackSelectorConfig(
            pt=(1.0 * u.GeV, None),
            absEta=(None, 3.0),
            loc0=(-4.0 * u.mm, 4.0 * u.mm),
            nMeasurementsMin=7,
            maxHoles=2,
            maxOutliers=2,
        )
    ),
    CkfConfig(
        chi2CutOffMeasurement=args.chi2[0],
        chi2CutOffOutlier=args.chi2[1],
        numMeasurementsCutOff=2,
        seedDeduplication=True,
        stayOnSeed=True,
        pixelVolumes=[16, 17, 18],
        stripVolumes=[23, 24, 25],
        maxPixelHoles=1,
        maxStripHoles=2,
        constrainToVolumes=[2, 32, 4, 16, 17, 18, 20, 23, 24, 25, 26, 8, 28, 29, 30],
        scatteringTailMode=args.mode,
    ),
    outputDirRoot=outRoot,
    writeCovMat=True,
    writeMatchingDetails=True,
)
addAmbiguityResolution(
    s,
    AmbiguityResolutionConfig(
        maximumSharedHits=3, maximumIterations=1000000, nMeasurementsMin=7
    ),
    outputDirRoot=outRoot,
    writeCovMat=True,
    writeMatchingDetails=True,
)

s.run()
