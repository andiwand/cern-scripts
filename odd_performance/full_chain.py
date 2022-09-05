#!/usr/bin/env python3
import pathlib
import acts, acts.examples
import acts.examples.dd4hep
from acts.examples.geant4 import Geant4Simulation, geant4SimulationConfig
from acts.examples.geant4.dd4hep import DDG4DetectorConstruction
from common import getOpenDataDetector, getOpenDataDetectorDirectory


geant4 = False

u = acts.UnitConstants
outputDir = pathlib.Path(__file__).parent / "odd_output"
outputDir.mkdir(exist_ok=True)

oddDir = getOpenDataDetectorDirectory()

oddMaterialMap = oddDir / "data/odd-material-maps.root"
oddDigiConfig = oddDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = oddDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(mdecorator=oddMaterialDeco)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

from particle_gun import addParticleGun, MomentumConfig, EtaConfig, ParticleConfig
from fatras import addFatras
from digitization import addDigitization
from seeding import addSeeding, SeedfinderConfigArg, SeedingAlgorithm
from ckf_tracks import addCKFTracks, CKFPerformanceConfig
from vertex_fitting import addVertexFitting, VertexFinder

s = acts.examples.Sequencer(events=100000, numThreads=-1, logLevel=acts.logging.INFO)

s = addParticleGun(
    s,
    MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, True),
    EtaConfig(-3.0, 3.0, True),
    ParticleConfig(1, acts.PdgParticle.eMuon, True),
    rnd=rnd,
)
if geant4:
    g4detector = DDG4DetectorConstruction(detector.geometryService)
    g4conf = geant4SimulationConfig(
        level=s.config.logLevel,
        detector=g4detector,
        inputParticles="particles_input",
        trackingGeometry=trackingGeometry,
        magneticField=field,
    )
    g4conf.outputSimHits = "simhits"
    g4conf.outputParticlesInitial = "particles_initial"
    g4conf.outputParticlesFinal = "particles_final"
    s.addAlgorithm(
        Geant4Simulation(
            level=s.config.logLevel,
            config=g4conf,
        )
    )
else:
    s = addFatras(
        s,
        trackingGeometry,
        field,
        outputDirRoot=outputDir,
        rnd=rnd,
    )
s = addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=oddDigiConfig,
    outputDirRoot=outputDir,
    rnd=rnd,
)
s = addSeeding(
    s,
    trackingGeometry,
    field,
    SeedfinderConfigArg(
        r=(20 * u.mm, 300 * u.mm),
        collisionRegion=(-250 * u.mm, 250 * u.mm),
        z=(-2000 * u.mm, 2000 * u.mm),
        maxSeedsPerSpM=4,
        bFieldInZ=2 * u.T,
        impactMax=3 * u.mm,
        cotThetaMax=17,
    ),
    geoSelectionConfigFile=oddSeedingSel,
    outputDirRoot=outputDir,
    logLevel=acts.logging.DEBUG,
)
"""
s = addCKFTracks(
    s,
    trackingGeometry,
    field,
    CKFPerformanceConfig(
        ptMin=400.0 * u.MeV,
        nMeasurementsMin=6,
    ),
    outputDirRoot=outputDir,
)
"""

s.run()
