#!/usr/bin/env python3
import pathlib, acts, acts.examples
from acts.examples.simulation import (
    addParticleGun,
    MomentumConfig,
    EtaConfig,
    ParticleConfig,
    addPythia8,
    addFatras,
    addDigitization,
)
from acts.examples.reconstruction import (
    addSeeding,
    SeedingAlgorithm,
    ParticleSmearingSigmas,
    addKalmanTracks,
    addCKFTracks,
    CKFPerformanceConfig,
    TrackSelectorRanges,
    addAmbiguityResolution,
    AmbiguityResolutionConfig,
    addVertexFitting,
    VertexFinder,
)
from common import getOpenDataDetectorDirectory
from acts.examples.odd import getOpenDataDetector

u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
outputDir = pathlib.Path.cwd() / "output"

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(
    geoDir, mdecorator=oddMaterialDeco
)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

s = acts.examples.Sequencer(events=100, numThreads=1, outputDir=str(outputDir))

"""
addParticleGun(
    s,
    MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, transverse=True),
    EtaConfig(-3.0, 3.0, uniform=True),
    ParticleConfig(2, acts.PdgParticle.eMuon, randomizeCharge=True),
    vtxGen=acts.examples.GaussianVertexGenerator(
        stddev=acts.Vector4(12.5 * u.um, 12.5 * u.um, 55.5 * u.mm, 10000.0 * u.ns),
        mean=acts.Vector4(0, 0, 0, 0),
    ),
    multiplicity=5,
    rnd=rnd,
)
"""

addPythia8(
    s,
    hardProcess=["Top:qqbar2ttbar=on"],
    npileup=50,
    vtxGen=acts.examples.GaussianVertexGenerator(
        stddev=acts.Vector4(12.5 * u.um, 12.5 * u.um, 55.5 * u.mm, 10000.0 * u.ns),
        mean=acts.Vector4(0, 0, 0, 0),
    ),
    rnd=rnd,
    outputDirRoot=outputDir,
)

addFatras(
    s,
    trackingGeometry,
    field,
    rnd=rnd,
    outputDirRoot=outputDir,
)

addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=oddDigiConfig,
    rnd=rnd,
    outputDirRoot=outputDir,
)

addSeeding(
    s,
    trackingGeometry,
    field,
    # ParticleSmearingSigmas(d0=20*u.um, d0PtA=0, d0PtB=0, z0=20*u.um, z0PtA=0, z0PtB=0),
    seedingAlgorithm=SeedingAlgorithm.TruthSmeared,
    geoSelectionConfigFile=oddSeedingSel,
    outputDirRoot=outputDir,
)

addKalmanTracks(
    s,
    trackingGeometry,
    field,
)

"""
addCKFTracks(
    s,
    trackingGeometry,
    field,
    CKFPerformanceConfig(ptMin=0.0, nMeasurementsMin=6),
    outputDirRoot=outputDir,
)

addAmbiguityResolution(
    s,
    AmbiguityResolutionConfig(maximumSharedHits=3),
    CKFPerformanceConfig(ptMin=0.0, nMeasurementsMin=6),
    outputDirRoot=outputDir,
)
"""

"""
s.addAlgorithm(acts.examples.TrackModifier(
    inputTrackParameters="trackParameters",
    outputTrackParameters="modifiedTrackParameters",
    dropCovariance=False,
    covScale=1,
    level=acts.logging.Level.DEBUG,
))
s.addWhiteboardAlias("trackParameters", "modifiedTrackParameters")
"""

addVertexFitting(
    s,
    field,
    TrackSelectorRanges(
        pt=(0.5 * u.GeV, None),
        loc0=(-4.0 * u.mm, 4.0 * u.mm),
        absEta=(None, 2.5),
        removeNeutral=True,
    ),
    vertexFinder=VertexFinder.AMVF,
    associatedParticles="particles_input",
    trackParametersTips=None,
    outputDirRoot=outputDir,
    logLevel=acts.logging.Level.VERBOSE,
)

s.run()
