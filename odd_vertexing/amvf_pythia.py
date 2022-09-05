#!/usr/bin/env python3
import pathlib, acts, acts.examples
from acts.examples.simulation import (
    addPythia8,
    addFatras,
    addDigitization,
)
from acts.examples.reconstruction import (
    addSeeding,
    SeedingAlgorithm,
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

s = acts.examples.Sequencer(events=100000, numThreads=1, outputDir=str(outputDir))

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
    seedingAlgorithm=SeedingAlgorithm.Default,
    geoSelectionConfigFile=oddSeedingSel,
    outputDirRoot=outputDir,
)

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
    outputDirRoot=outputDir,
    logLevel=acts.logging.Level.VERBOSE,
)

s.run()
