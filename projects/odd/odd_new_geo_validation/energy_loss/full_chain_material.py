#!/usr/bin/env python3

import pathlib, acts, acts.examples
from acts.examples.simulation import (
    addParticleGun,
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    addFatras,
    addGeant4,
    addDigitization,
)
from acts.examples.reconstruction import (
    addSeedingTruthSelection,
    TruthSeedRanges,
    TruthEstimatedSeedingAlgorithmConfigArg,
    addSeeding,
    ParticleSmearingSigmas,
    SeedingAlgorithm,
    addKalmanTracks,
    addCKFTracks,
    CKFPerformanceConfig,
)
import acts.examples.geant4
from common import getOpenDataDetectorDirectory

import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], ".."))
import gdml_geometry

import argparse


parser = argparse.ArgumentParser()
parser.add_argument("sim", choices=["fatras", "geant4"])
parser.add_argument("pT", type=float)
parser.add_argument("-n", "--number-of-events", default=1000)
parser.add_argument("-m", "--number-of-particles", default=100)
parser.add_argument("-o", "--output-path", default="root_files")
args = parser.parse_args()


u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
rootOutputDir = pathlib.Path.cwd() / args.output_path

oddDigiConfig = pathlib.Path.cwd() / "../odd-light-digi-smearing-config.json"
oddSeedingSel = pathlib.Path.cwd() / "../odd-light-seeding-config.json"

g4detectorConstruction = acts.examples.geant4.GdmlDetectorConstruction(
    "../odd-light.gdml"
)
trackingGeometry, decorators, detectorElements = gdml_geometry.trackingGeometryFromGDML(
    "../odd-light.gdml",
    "../odd-light-proto-detector.json",
    "odd-light",
    ["sens_vol"],
    ["pass_vol"],
)
field = acts.ConstantBField(acts.Vector3(0.0 * u.T, 0.0 * u.T, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

s = acts.examples.Sequencer(events=args.number_of_events, numThreads=1)

addParticleGun(
    s,
    MomentumConfig(args.pT * u.GeV, args.pT * u.GeV, transverse=True),
    # PhiConfig(0.5, 0.5),
    EtaConfig(-3.0, 3.0, uniform=True),
    ParticleConfig(
        args.number_of_particles, acts.PdgParticle.eMuon, randomizeCharge=True
    ),
    vtxGen=acts.examples.GaussianVertexGenerator(
        mean=acts.Vector4(0, 0, 0, 0),
        stddev=acts.Vector4(0, 0, 0, 0),
    ),
    multiplicity=1,
    rnd=rnd,
    outputDirRoot=rootOutputDir,
)

if args.sim == "fatras":
    addFatras(
        s,
        trackingGeometry=trackingGeometry,
        field=field,
        enableInteractions=True,
        rnd=rnd,
        outputDirRoot=rootOutputDir,
    )
else:
    addGeant4(
        s,
        detector=None,
        g4detectorConstruction=g4detectorConstruction,
        trackingGeometry=trackingGeometry,
        field=field,
        volumeMappings=[],
        materialMappings=["Material_G4_Si"],
        rnd=rnd,
        outputDirRoot=rootOutputDir,
    )

addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=oddDigiConfig,
    rnd=rnd,
    outputDirRoot=rootOutputDir,
)

addSeeding(
    s,
    trackingGeometry,
    field,
    truthSeedRanges=None,
    seedingAlgorithm=SeedingAlgorithm.TruthEstimated,
    truthEstimatedSeedingAlgorithmConfigArg=TruthEstimatedSeedingAlgorithmConfigArg(
        deltaR=(10.0 * u.mm, None)
    ),
    initialVarInflation=[100, 100, 100, 100, 100, 1e3],
    geoSelectionConfigFile=oddSeedingSel,
    inputParticles="particles_input",
    outputDirRoot=rootOutputDir,
    # logLevel=acts.logging.VERBOSE,
)

if True:
    addKalmanTracks(
        s,
        trackingGeometry,
        field,
        multipleScattering=True,
        energyLoss=True,
        reverseFilteringMomThreshold=0 * u.GeV,
        # logLevel=acts.logging.VERBOSE,
    )
else:
    addCKFTracks(
        s,
        trackingGeometry,
        field,
        CKFPerformanceConfig(
            ptMin=0.0,
            nMeasurementsMin=6,
        ),
    )

s.addWriter(
    acts.examples.RootTrajectorySummaryWriter(
        level=acts.logging.INFO,
        inputTrajectories="trajectories",
        inputParticles="particles_input",
        inputMeasurementParticlesMap="measurement_particles_map",
        filePath=str(rootOutputDir / "tracksummary_kalman.root"),
        treeName="tracksummary",
    )
)

s.addWriter(
    acts.examples.RootTrajectoryStatesWriter(
        level=acts.logging.INFO,
        inputTrajectories="trajectories",
        inputParticles="particles_input",
        inputSimHits="simhits",
        inputMeasurementParticlesMap="measurement_particles_map",
        inputMeasurementSimHitsMap="measurement_simhits_map",
        filePath=str(rootOutputDir / f"trackstates_kalman.root"),
        treeName="trackstates",
    )
)

s.run()
