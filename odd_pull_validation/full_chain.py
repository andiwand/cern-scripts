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
from acts.examples.odd import getOpenDataDetector


u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
rootOutputDir = pathlib.Path.cwd() / "output"

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(
    geoDir, mdecorator=oddMaterialDeco
)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

s = acts.examples.Sequencer(events=10000, numThreads=1)

particleConfig = ParticleConfig(
    1,
    acts.PdgParticle.eMuon,
    randomizeCharge=True,
)

addParticleGun(
    s,
    MomentumConfig(1 * u.GeV, 10 * u.GeV, transverse=True),
    EtaConfig(-3.0, 3.0, uniform=True),
    particleConfig,
    vtxGen=acts.examples.GaussianVertexGenerator(
        mean=acts.Vector4(0, 0, 0, 0),
        stddev=acts.Vector4(0, 0, 0, 0),
    ),
    multiplicity=1,
    rnd=rnd,
    outputDirRoot=rootOutputDir,
)

if True:
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
        detector,
        trackingGeometry,
        field,
        recordHitsOfSecondaries=False,
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
    seedingAlgorithm=SeedingAlgorithm.TruthSmeared,
    truthEstimatedSeedingAlgorithmConfigArg=TruthEstimatedSeedingAlgorithmConfigArg(
        deltaR=(10.0 * u.mm, None)
    ),
    initialVarInflation=[100, 100, 100, 100, 100, 100],
    geoSelectionConfigFile=oddSeedingSel,
    inputParticles="particles_input",
    outputDirRoot=rootOutputDir,
    # logLevel=acts.logging.VERBOSE,
)

if False:
    addKalmanTracks(
        s,
        trackingGeometry,
        field,
        multipleScattering=True,
        energyLoss=True,
        reverseFilteringMomThreshold=0 * u.GeV,
        # logLevel=acts.logging.VERBOSE,
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
else:
    addCKFTracks(
        s,
        trackingGeometry,
        field,
        CKFPerformanceConfig(
            ptMin=0.0,
            nMeasurementsMin=6,
        ),
        outputDirRoot=rootOutputDir,
    )

s.run()
