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
    ParticleSelectorConfig,
    addFatras,
    addGeant4,
    addDigitization,
)
from acts.examples.reconstruction import (
    SeedFinderConfigArg,
    addSeeding,
    TrackSelectorConfig,
    CkfConfig,
    addCKFTracks,
    AmbiguityResolutionConfig,
    addAmbiguityResolution,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory


u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
outputDir = Path.cwd() / "output"
outputDir.mkdir(parents=True, exist_ok=True)

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(
    odd_dir=geoDir, mdecorator=oddMaterialDeco
)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)


skip = 0
events = 10000
geant4 = False
smearedDigi = True
logLevel = acts.logging.INFO
debug = False

if debug:
    skip = 3735
    events = 1
    logLevel = acts.logging.VERBOSE


if smearedDigi:
    oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
else:
    oddDigiConfig = geoDir / "config/odd-digi-geometric-config.json"


s = acts.examples.Sequencer(
    skip=skip,
    events=events,
    numThreads=1,
    outputDir=str(outputDir),
    trackFpes=False,
    # logLevel=acts.logging.WARNING,
)

addParticleGun(
    s,
    MomentumConfig(100.0 * u.GeV, 100.0 * u.GeV, transverse=True),
    EtaConfig(-3.0, 3.0, uniform=True),
    PhiConfig(0.0, 360.0 * u.degree),
    ParticleConfig(1, acts.PdgParticle.eMuon, randomizeCharge=True),
    vtxGen=acts.examples.GaussianVertexGenerator(
        mean=acts.Vector4(0, 0, 0, 0),
        stddev=acts.Vector4(
            0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 1.0 * u.ns
        ),
    ),
    multiplicity=1,
    rnd=rnd,
    # outputDirRoot=outputDir,
    # outputDirCsv=outputDir,
)

if not geant4:
    addFatras(
        s,
        trackingGeometry,
        field,
        preSelectParticles=ParticleSelectorConfig(
            rho=(0.0, 24 * u.mm),
            absZ=(0.0, 1.0 * u.m),
            eta=(-3.0, 3.0),
            pt=(150 * u.MeV, None),
            removeNeutral=True,
        ),
        postSelectParticles=ParticleSelectorConfig(
            # these cuts should not be necessary for sim
            eta=(-3.0, 3.0),
            # using something close to 1 to include for sure
            pt=(0.9 * u.GeV, None),
            removeNeutral=True,
        ),
        enableInteractions=False,
        outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
        rnd=rnd,
        logLevel=logLevel,
    )
else:
    addGeant4(
        s,
        detector,
        trackingGeometry,
        field,
        preSelectParticles=ParticleSelectorConfig(
            rho=(0.0, 24 * u.mm),
            absZ=(0.0, 1.0 * u.m),
            eta=(-3.0, 3.0),
            pt=(150 * u.MeV, None),
            removeNeutral=True,
        ),
        postSelectParticles=ParticleSelectorConfig(
            # these cuts should not be necessary for sim
            eta=(-3.0, 3.0),
            # using something close to 1 to include for sure
            pt=(0.9 * u.GeV, None),
            removeNeutral=True,
        ),
        outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
        rnd=rnd,
        killVolume=trackingGeometry.worldVolume,
        killAfterTime=25 * u.ns,
        recordHitsOfSecondaries=False,
    )

addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=oddDigiConfig,
    outputDirRoot=outputDir,
    # outputDirCsv=outputDir,
    rnd=rnd,
)

addSeeding(
    s,
    trackingGeometry,
    field,
    geoSelectionConfigFile=oddSeedingSel,
    seedFinderConfigArg=SeedFinderConfigArg(
        #r=(33 * u.mm, 200 * u.mm),
        #deltaR=(1 * u.mm, 60 * u.mm),
        #collisionRegion=(-250 * u.mm, 250 * u.mm),
        #z=(-2000 * u.mm, 2000 * u.mm),
        #maxSeedsPerSpM=1,
        #sigmaScattering=5,
        #radLengthPerSeed=0.1,
        minPt=0.9 * u.GeV,
        #impactMax=3 * u.mm,
    ),
    initialSimgaQoverPCoefficients=[0.0, 0.0, 0.0, 0.0, 100.0, 0.0],
    outputDirRoot=outputDir,
    # outputDirCsv=outputDir,
)

addCKFTracks(
    s,
    trackingGeometry,
    field,
    TrackSelectorConfig(
        pt=(1.0 * u.GeV, None),
        absEta=(None, 3.1),
        loc0=(-4.0 * u.mm, 4.0 * u.mm),
        nMeasurementsMin=3,
        maxHoles=2,
        maxOutliers=2,
    ),
    CkfConfig(
        chi2CutOff=15,
        numMeasurementsCutOff=1,
        seedDeduplication=True,
        stayOnSeed=True,
    ),
    # outputDirCsv=outputDir,
    # outputDirRoot=outputDir,
    writeCovMat=False,
    logLevel=logLevel,
)

addAmbiguityResolution(
    s,
    AmbiguityResolutionConfig(
        maximumSharedHits=3,
        maximumIterations=1000000,
        nMeasurementsMin=3,
    ),
    # outputDirCsv=outputDir,
    outputDirRoot=outputDir,
    writeCovMat=False,
)

s.run()
