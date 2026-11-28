#!/usr/bin/env python3
"""Single-thread ODD full chain, run in rounds, per-event time of one stage.

    full_chain_perf.py OUT [--stage ckf|seeding|kf|gsf] [--ttbar | --geant4 DIR]

Appends one row per round to OUT/times.csv with the per-event time of the
timed algorithms of the stage:

    ckf      fatras, seeding, ckf  (grid triplet seeds, CKF)
    seeding  fatras, seeding       (grid triplet seeds, looser seed cuts)
    kf       kf                    (truth tracks, Kalman fitter)
    gsf      gsf                   (truth tracks, GSF on electrons)

Input is a particle gun (muons, electrons for gsf), Pythia8 ttbar with
pile-up (--ttbar), or a Geant4 simulation read from DIR (particles.root,
vertices.root, particles_simulation.root, hits.root).

Environment, for compatibility with older runs: CKF_RUNS, CKF_EVENTS,
CKF_PILEUP set the defaults of --runs, --events, --pileup;
CKF_RECORD_MATERIAL_STATES=0/1 and CKF_LOG_LEVEL=<level> are passed to the
CKF only when set, so builds without the option still work.
"""

import argparse
import os
from pathlib import Path

import pandas as pd

import acts
import acts.examples
import acts.examples.root
from acts.examples.simulation import (
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    addParticleGun,
    addPythia8,
    addGenParticleSelection,
    ParticleSelectorConfig,
    addFatras,
    addDigitization,
    addDigiParticleSelection,
)
from acts.examples.reconstruction import (
    SeedingAlgorithm,
    SeedFinderConfigArg,
    SeedFinderOptionsArg,
    SeedFilterConfigArg,
    SpacePointGridConfigArg,
    addSeeding,
    TrackSelectorConfig,
    CkfConfig,
    addCKFTracks,
    addKalmanTracks,
    addTruthTrackingGsf,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

# (events, runs) for particle gun, ttbar and Geant4 input
DEFAULTS = {
    "ckf": ((20, 50), (3, 30), (1, 30)),
    "seeding": ((20, 50), (5, 50), (3, 30)),
    "kf": ((20, 50), (3, 30), (10, 10)),
    "gsf": ((5, 30), (5, 50), (10, 10)),
}

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument("outputDir", help="Output directory", type=Path)
parser.add_argument("--stage", choices=sorted(DEFAULTS), default="ckf")
parser.add_argument("--ttbar", help="Use ttbar events", action="store_true")
parser.add_argument("--geant4", help="Use geant4 simulation files", type=Path)
parser.add_argument("--events", type=int, help="events per round")
parser.add_argument("--runs", type=int, help="number of rounds")
parser.add_argument(
    "--pileup", type=int, default=int(os.environ.get("CKF_PILEUP", 200))
)
parser.add_argument(
    "--write",
    action="store_true",
    help="ckf: write track summaries and states (CSV and ROOT) to compare "
    "outputs between builds; leave off for timing",
)
args = parser.parse_args()

u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
outputDir = Path.cwd() / args.outputDir
outputDir.mkdir(parents=True, exist_ok=True)

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector = getOpenDataDetector(odd_dir=geoDir, materialDecorator=oddMaterialDeco)
trackingGeometry = detector.trackingGeometry()

field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

gun, ttbar, geant4 = DEFAULTS[args.stage]
events, runs = geant4 if args.geant4 else ttbar if args.ttbar else gun
if args.geant4 is None:
    runs = int(os.environ.get("CKF_RUNS", runs))
    events = int(os.environ.get("CKF_EVENTS", events))
events = args.events if args.events is not None else events
runs = args.runs if args.runs is not None else runs


def add_input(s):
    if args.geant4 is not None:
        for reader, kwargs in [
            (
                acts.examples.root.RootParticleReader,
                dict(
                    outputParticles="particles_generated_selected",
                    filePath=args.geant4 / "particles.root",
                ),
            ),
            (
                acts.examples.root.RootVertexReader,
                dict(
                    outputVertices="vertices_generated",
                    filePath=args.geant4 / "vertices.root",
                ),
            ),
            (
                acts.examples.root.RootParticleReader,
                dict(
                    outputParticles="particles_simulated",
                    filePath=args.geant4 / "particles_simulation.root",
                ),
            ),
            (
                acts.examples.root.RootSimHitReader,
                dict(
                    outputSimHits="simhits",
                    treeName="hits",
                    filePath=args.geant4 / "hits.root",
                ),
            ),
        ]:
            s.addReader(reader(level=acts.logging.WARNING, **kwargs))
        s.addWhiteboardAlias("particles", "particles_simulated")
        s.addWhiteboardAlias("particles_simulated_selected", "particles_simulated")
        return

    if not args.ttbar:
        electrons = args.stage == "gsf"
        addParticleGun(
            s,
            MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, transverse=True),
            EtaConfig(-3.0, 3.0, uniform=True),
            PhiConfig(0.0, 360.0 * u.degree),
            ParticleConfig(
                4,
                acts.PdgParticle.eElectron if electrons else acts.PdgParticle.eMuon,
                randomizeCharge=True,
            ),
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(
                    0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 1.0 * u.ns
                ),
            ),
            multiplicity=10 if electrons else 50,
            rnd=rnd,
        )
    else:
        addPythia8(
            s,
            hardProcess=["Top:qqbar2ttbar=on"],
            npileup=args.pileup,
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(
                    0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns
                ),
            ),
            rnd=rnd,
        )

    addGenParticleSelection(
        s,
        ParticleSelectorConfig(
            rho=(0.0, 24 * u.mm),
            absZ=(0.0, 1.0 * u.m),
        ),
    )

    addFatras(
        s,
        trackingGeometry,
        field,
        enableInteractions=True,
        rnd=rnd,
    )


def add_seeding(s):
    if args.stage in ("kf", "gsf"):
        addSeeding(
            s,
            trackingGeometry,
            field,
            seedingAlgorithm=SeedingAlgorithm.TruthEstimated,
            geoSelectionConfigFile=oddSeedingSel,
        )
        return

    if args.stage == "seeding":
        extra = dict(
            seedFinderConfigArg=SeedFinderConfigArg(
                r=(33 * u.mm, 200 * u.mm),
                deltaR=(1 * u.mm, 300 * u.mm),
                collisionRegion=(-250 * u.mm, 250 * u.mm),
                z=(-2000 * u.mm, 2000 * u.mm),
                maxSeedsPerSpM=3,
                sigmaScattering=5,
                radLengthPerSeed=0.1,
                minPt=0.5 * u.GeV,
                impactMax=3 * u.mm,
                interactionPointCut=True,
            ),
            seedFinderOptionsArg=SeedFinderOptionsArg(bFieldInZ=2.0 * u.T),
            seedFilterConfigArg=SeedFilterConfigArg(),
            spacePointGridConfigArg=SpacePointGridConfigArg(
                impactMax=0 * u.mm,
                rMax=200 * u.mm,
            ),
        )
    else:
        extra = dict(
            seedFinderConfigArg=SeedFinderConfigArg(
                r=(33 * u.mm, 200 * u.mm),
                deltaR=(1 * u.mm, 300 * u.mm),
                collisionRegion=(-250 * u.mm, 250 * u.mm),
                z=(-2000 * u.mm, 2000 * u.mm),
                maxSeedsPerSpM=3,
                sigmaScattering=5,
                radLengthPerSeed=0.1,
                minPt=0.8 * u.GeV,
                impactMax=3 * u.mm,
            ),
            seedFilterConfigArg=SeedFilterConfigArg(seedConfirmation=True),
        )

    addSeeding(
        s,
        trackingGeometry,
        field,
        seedingAlgorithm=SeedingAlgorithm.GridTriplet,
        geoSelectionConfigFile=oddSeedingSel,
        **extra,
    )


def add_tracking(s):
    if args.stage == "ckf":
        write = args.write
        addCKFTracks(
            s,
            trackingGeometry,
            field,
            TrackSelectorConfig(
                pt=(1.0 * u.GeV, None),
                absEta=(None, 3.0),
                loc0=(-4.0 * u.mm, 4.0 * u.mm),
                nMeasurementsMin=7,
                maxHoles=2,
                maxOutliers=2,
                maxHolesAndOutliers=4,
            ),
            CkfConfig(
                chi2CutOffMeasurement=9,
                chi2CutOffOutlier=15,
                numMeasurementsCutOff=1,
                seedDeduplication=True,
                stayOnSeed=True,
                **(
                    {
                        "recordMaterialStates": os.environ[
                            "CKF_RECORD_MATERIAL_STATES"
                        ]
                        == "1"
                    }
                    if "CKF_RECORD_MATERIAL_STATES" in os.environ
                    else {}
                ),
            ),
            logLevel=getattr(acts.logging, os.environ["CKF_LOG_LEVEL"])
            if "CKF_LOG_LEVEL" in os.environ
            else None,
            outputDirCsv=outputDir if write else None,
            outputDirRoot=outputDir if write else None,
            writeTrackStates=write,
            writeCovMat=write,
            writePerformance=False if write else True,
        )
    elif args.stage == "kf":
        addKalmanTracks(
            s,
            trackingGeometry,
            field,
            reverseFilteringMomThreshold=0 * u.GeV,
            inputProtoTracks="truth_particle_tracks",
            multipleScattering=True,
            energyLoss=True,
            clusters=None,
            calibrator=acts.examples.makePassThroughCalibrator(),
        )
    elif args.stage == "gsf":
        addTruthTrackingGsf(
            s,
            trackingGeometry,
            field,
            inputProtoTracks="truth_particle_tracks",
        )


def create_sequencer():
    s = acts.examples.Sequencer(
        events=events,
        numThreads=1,
        outputDir=str(outputDir),
        trackFpes=False,
    )

    add_input(s)

    addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=oddDigiConfig,
        rnd=rnd,
    )

    addDigiParticleSelection(
        s,
        ParticleSelectorConfig(
            eta=(-3.0, 3.0),
            pt=(0.9 * u.GeV, None),
            removeNeutral=True,
            **({"measurements": (7, None)} if args.stage in ("kf", "gsf") else {}),
        ),
    )

    add_seeding(s)
    add_tracking(s)
    return s


TIMED = {
    "fatras": "Algorithm:FatrasSimulation",
    "seeding": "Algorithm:GridTripletSeedingAlgorithm",
    "ckf": "Algorithm:TrackFindingAlgorithm",
    "kf": "Algorithm:TrackFittingAlgorithm",
    "gsf": "Algorithm:TrackFittingAlgorithm",
}
timed = {
    "ckf": ["fatras", "seeding", "ckf"],
    "seeding": ["fatras", "seeding"],
    "kf": ["kf"],
    "gsf": ["gsf"],
}[args.stage]
if args.geant4 is not None:
    timed = [t for t in timed if t != "fatras"]

s = create_sequencer()

times = []
for i in range(runs):
    print(f"start round {i}")
    s.run()
    d = pd.read_csv(outputDir / "timing.csv")
    t = {
        name: d[d["identifier"] == TIMED[name]]["time_perevent_s"].values[0]
        for name in timed
    }
    print(f"finished and got times {t}")
    times.append(t)
    pd.DataFrame(times).to_csv(outputDir / "times.csv", index=False)
