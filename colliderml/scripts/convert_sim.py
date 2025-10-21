#!/usr/bin/env python3

import pathlib

import acts
import acts.examples
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addSimParticleSelection,
    addDigitization,
    addDigiParticleSelection,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory
import acts.examples.edm4hep
from acts.examples.podio import PodioReader

u = acts.UnitConstants


inputFile = "/Users/andreas/Downloads/edm4hep.root"
outputDir = pathlib.Path(__file__).parent / "colliderml_output"
geoDir = getOpenDataDetectorDirectory()
actsDir = pathlib.Path(__file__).parent

oddDigiConfig = actsDir / "Examples/Configs/odd-digi-smearing-config.json"
oddSeedingSel = actsDir / "Examples/Configs/odd-seeding-config.json"
oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector = getOpenDataDetector(odd_dir=geoDir, materialDecorator=oddMaterialDeco)
trackingGeometry = detector.trackingGeometry()
decorators = detector.contextDecorators()
field = detector.field
rnd = acts.examples.RandomNumbers(seed=42)

s = acts.examples.Sequencer(
    events=1,
    skip=0,
    numThreads=-1,
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
)

addDigiParticleSelection(
    s,
    ParticleSelectorConfig(
        # we are only interested in the hard scatter vertex
        #primaryVertexId=(1, 2),
        rho=(0.0, 24 * u.mm),
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

s.addWriter(
    acts.examples.RootParticleWriter(
        level=acts.logging.DEBUG,
        inputParticles="particles_selected",
        filePath=str(outputDir / "particles_selected.root"),
    )
)

s.run()
