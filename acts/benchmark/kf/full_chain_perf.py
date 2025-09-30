#!/usr/bin/env python3

from pathlib import Path

import acts
import acts.examples
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
    addSeeding,
    addKalmanTracks,
    addTrackWriters,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("outputDir", help="Output directory", type=Path)
parser.add_argument("--ttbar", help="Use ttbar events", action="store_true")
parser.add_argument("--geant4", help="Use geant4 simulation files", type=Path)
args = parser.parse_args()

u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
outputDir = Path.cwd() / args.outputDir
outputDir.mkdir(parents=True, exist_ok=True)

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector = getOpenDataDetector(
    odd_dir=geoDir, materialDecorator=oddMaterialDeco
)
trackingGeometry = detector.trackingGeometry()

field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)


events = 20
runs = 50

if args.ttbar:
    events = 5
    runs = 50

if args.geant4 is not None:
    events = 10
    runs = 10


def create_sequencer():
    s = acts.examples.Sequencer(
        events=events,
        numThreads=1,
        outputDir=str(outputDir),
        trackFpes=False,
        # logLevel=acts.logging.WARNING,
    )

    if args.geant4 is None:
        if not args.ttbar:
            addParticleGun(
                s,
                MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, transverse=True),
                EtaConfig(-3.0, 3.0, uniform=True),
                PhiConfig(0.0, 360.0 * u.degree),
                ParticleConfig(4, acts.PdgParticle.eMuon, randomizeCharge=True),
                vtxGen=acts.examples.GaussianVertexGenerator(
                    mean=acts.Vector4(0, 0, 0, 0),
                    stddev=acts.Vector4(
                        0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 1.0 * u.ns
                    ),
                ),
                multiplicity=50,
                rnd=rnd,
                # outputDirRoot=outputDir,
                # outputDirCsv=outputDir,
            )
        else:
            addPythia8(
                s,
                hardProcess=["Top:qqbar2ttbar=on"],
                npileup=200,
                vtxGen=acts.examples.GaussianVertexGenerator(
                    mean=acts.Vector4(0, 0, 0, 0),
                    stddev=acts.Vector4(
                        0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns
                    ),
                ),
                rnd=rnd,
                # outputDirRoot=outputDir,
                # outputDirCsv=outputDir,
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
            # outputDirRoot=outputDir,
            # outputDirCsv=outputDir,
            rnd=rnd,
        )
    else:
        s.addReader(
            acts.examples.RootParticleReader(
                level=acts.logging.WARNING,
                outputParticles="particles_generated_selected",
                filePath=args.geant4 / "particles.root",
            )
        )
        s.addReader(
            acts.examples.RootVertexReader(
                level=acts.logging.WARNING,
                outputVertices="vertices_generated",
                filePath=args.geant4 / "vertices.root",
            )
        )
        s.addReader(
            acts.examples.RootParticleReader(
                level=acts.logging.WARNING,
                outputParticles="particles_simulated",
                filePath=args.geant4 / "particles_simulation.root",
            )
        )
        s.addReader(
            acts.examples.RootSimHitReader(
                level=acts.logging.WARNING,
                outputSimHits="simhits",
                treeName="hits",
                filePath=args.geant4 / "hits.root",
            )
        )

        s.addWhiteboardAlias("particles", "particles_simulated")
        s.addWhiteboardAlias(
            "particles_simulated_selected", "particles_simulated"
        )

    addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=oddDigiConfig,
        # outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
        rnd=rnd,
    )

    addDigiParticleSelection(
        s,
        ParticleSelectorConfig(
            eta=(-3.0, 3.0),
            pt=(0.9 * u.GeV, None),
            measurements=(7, None),
            removeNeutral=True,
        ),
    )

    addSeeding(
        s,
        trackingGeometry,
        field,
        seedingAlgorithm=SeedingAlgorithm.TruthEstimated,
        geoSelectionConfigFile=oddSeedingSel,
        # outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
    )

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
        # logLevel=acts.logging.DEBUG,
    )

    """
    addTrackWriters(
        s,
        name="kf",
        tracks="kf_tracks",
        # outputDirCsv=outputDir,
        outputDirRoot=outputDir,
        writeSummary=True,
        writeStates=False,
        writeFitterPerformance=True,
        writeFinderPerformance=True,
        writeCovMat=False,
        logLevel=acts.logging.INFO,
    )
    """

    return s


import pandas as pd

s = create_sequencer()

times = []
for i in range(runs):
    print(f"start round {i}")
    s.run()
    d = pd.read_csv(outputDir / "timing.csv")
    t = {}
    t["kf"] = d[d["identifier"] == "Algorithm:TrackFittingAlgorithm"][
        "time_perevent_s"
    ].values[0]
    print(f"finished and got times {t}")
    times.append(t)
    pd.DataFrame(times).to_csv(outputDir / "times.csv", index=False)
