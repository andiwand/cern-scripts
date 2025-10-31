#!/usr/bin/env python3

import os
import argparse
from pathlib import Path

import acts
import acts.examples
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addSimParticleSelection,
    addDigitization,
    addDigiParticleSelection,
)
from acts.examples.reconstruction import (
    SeedingAlgorithm,
    SeedFinderConfigArg,
    addSeeding,
    CkfConfig,
    addCKFTracks,
    TrackSelectorConfig,
    addAmbiguityResolution,
    AmbiguityResolutionConfig,
    addVertexFitting,
    VertexFinder,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory
import acts.examples.edm4hep
from acts.examples.podio import PodioReader

u = acts.UnitConstants


parser = argparse.ArgumentParser()
parser.add_argument("--input-file", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--events", type=int, required=True)
parser.add_argument("--threads", type=int, default=-1)
args = parser.parse_args()


inputFile = args.input_file
outputDir = args.output_dir
geoDir = getOpenDataDetectorDirectory()
actsDir = Path(os.getenv("ACTS_SOURCE_DIR"))

oddDigiConfig = actsDir / "Examples/Configs/odd-digi-smearing-config.json"
oddDigiConfig = Path(__file__).parent / "odd-digi-geometric-config.json"
oddSeedingSel = actsDir / "Examples/Configs/odd-seeding-config.json"
oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector = getOpenDataDetector(odd_dir=geoDir, materialDecorator=oddMaterialDeco)
trackingGeometry = detector.trackingGeometry()
decorators = detector.contextDecorators()
field = detector.field
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 3.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

s = acts.examples.Sequencer(
    events=args.events,
    skip=0,
    numThreads=args.threads,
    outputDir=str(outputDir),
)

s.addReader(
    PodioReader(
        level=acts.logging.DEBUG,
        inputPath=str(inputFile),
        outputFrame="events",
        category="events",
    )
)

edm4hepReader = acts.examples.edm4hep.EDM4hepSimInputConverter(
    inputFrame="events",
    inputSimHits=[
        "PixelBarrelReadout",
        "PixelEndcapReadout",
        "ShortStripBarrelReadout",
        "ShortStripEndcapReadout",
        "LongStripBarrelReadout",
        "LongStripEndcapReadout",
    ],
    outputParticlesGenerator="particles_generated",
    outputParticlesSimulation="particles_simulated",
    outputSimHits="simhits",
    outputSimVertices="vertices_truth",
    dd4hepDetector=detector,
    trackingGeometry=trackingGeometry,
    sortSimHitsInTime=False,
    particleRMax=1080 * u.mm,
    particleZ=(-3030 * u.mm, 3030 * u.mm),
    particlePtMin=150 * u.MeV,
    level=acts.logging.DEBUG,
)
s.addAlgorithm(edm4hepReader)

s.addWhiteboardAlias("particles", edm4hepReader.config.outputParticlesSimulation)

addSimParticleSelection(
    s,
    ParticleSelectorConfig(),
)

s.addWriter(
    acts.examples.RootParticleWriter(
        level=acts.logging.DEBUG,
        inputParticles="particles_generated",
        filePath=str(outputDir / "particles_generated.root"),
    )
)

s.addWriter(
    acts.examples.RootParticleWriter(
        level=acts.logging.DEBUG,
        inputParticles="particles_simulated",
        filePath=str(outputDir / "particles_simulated.root"),
    )
)

s.addWriter(
    acts.examples.RootVertexWriter(
        level=acts.logging.DEBUG,
        inputVertices="vertices_truth",
        filePath=str(outputDir / "vertices.root"),
    )
)

s.addWriter(
    acts.examples.RootSimHitWriter(
        level=acts.logging.DEBUG,
        inputSimHits="simhits",
        filePath=str(outputDir / "hits.root"),
    )
)

addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=oddDigiConfig,
    outputDirRoot=outputDir,
    rnd=rnd,
)

def make_geoid(vol=None, lay=None):
    geoid = acts.GeometryIdentifier()
    if vol is not None:
        geoid.volume = vol
    if lay is not None:
        geoid.layer = lay
    return geoid

measurementCounter = acts.examples.ParticleSelector.MeasurementCounter()
# At least 3 hits in the pixels
measurementCounter.addCounter(
    [
        make_geoid(16),
        make_geoid(17),
        make_geoid(18),
    ],
    3,
    1,
)

addDigiParticleSelection(
    s,
    ParticleSelectorConfig(
        # we are only interested in the hard scatter vertex
        #primaryVertexId=(1, 2),
        rho=(0.0, 23 * u.mm),
        absZ=(0.0, 1.0 * u.m),
        eta=(-3.0, 3.0),
        # using something close to 1 to include for sure
        pt=(0.999 * u.GeV, None),
        measurements=(6, None),
        removeNeutral=True,
        removeSecondaries=False,
        nMeasurementsGroupMin=measurementCounter,
    ),
)

addSeeding(
    s,
    trackingGeometry,
    field,
    seedingAlgorithm=SeedingAlgorithm.Default,
    particleHypothesis=acts.ParticleHypothesis.pion,
    seedFinderConfigArg=SeedFinderConfigArg(
        r=(33 * u.mm, 200 * u.mm),
        # kills efficiency at |eta|~2
        deltaR=(10 * u.mm, 200 * u.mm),
        collisionRegion=(-250 * u.mm, 250 * u.mm),
        z=(-2000 * u.mm, 2000 * u.mm),
        maxSeedsPerSpM=40,
        sigmaScattering=5,
        radLengthPerSeed=0.1,
        minPt=0.5 * u.GeV,
        impactMax=3 * u.mm,
        zBinEdges=[-1600, -1000, -600, 0, 600, 1000, 1600],
    ),
    initialSigmas = [
        1 * u.mm,
        1 * u.mm,
        1 * u.degree,
        1 * u.degree,
        0 / u.GeV,
        1 * u.ns,
    ],
    initialSigmaQoverPt=0.1 * u.e / u.GeV,
    initialSigmaPtRel = 0.1,
    initialVarInflation = [1e0, 1e0, 1e0, 1e0, 1e0, 1e0],
    geoSelectionConfigFile=oddSeedingSel,
    outputDirRoot=outputDir,
)

addCKFTracks(
    s,
    trackingGeometry,
    field,
    trackSelectorConfig=TrackSelectorConfig(
        pt=(0.7 * u.GeV, None),
        absEta=(None, 3.5),
        nMeasurementsMin=6,
        maxHolesAndOutliers=3,
    ),
    ckfConfig=CkfConfig(
        chi2CutOffMeasurement=15.0,
        chi2CutOffOutlier=25.0,
        numMeasurementsCutOff=1,
        seedDeduplication=True,
        stayOnSeed=True,
    ),
    twoWay=True,
    outputDirRoot=outputDir,
)

addAmbiguityResolution(
    s,
    config=AmbiguityResolutionConfig(
        maximumSharedHits=3,
        maximumIterations=1000000,
        nMeasurementsMin=6,
    ),
    outputDirRoot=outputDir,
)

addVertexFitting(
    s,
    field,
    vertexFinder=VertexFinder.AMVF,
    outputDirRoot=outputDir,
)

s.run()
