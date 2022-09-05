#!/usr/bin/env python3

import argparse

import acts
import acts.examples


def trackingGeometryFromGDML(
    gdmlFile,
    protoFile,
    trackingGeometryName,
    sensitiveTags,
    passiveTags,
    logLevel=acts.logging.VERBOSE,
):
    g4DetectorConstruction = acts.examples.geant4.GdmlDetectorConstruction(gdmlFile)
    g4World = g4DetectorConstruction.Construct()

    protoDetector = acts.examples.ProtoDetector(protoFile)

    g4SensitiveSelector = acts.examples.geant4.VolumeNameSelector(sensitiveTags, False)
    g4PassiveSelector = acts.examples.geant4.VolumeNameSelector(passiveTags, False)

    g4SurfaceOptions = acts.examples.geant4.SurfaceFactoryOptions()
    g4SurfaceOptions.sensitiveSurfaceSelector = g4SensitiveSelector
    g4SurfaceOptions.passiveSurfaceSelector = g4PassiveSelector

    g4DetectorCfg = acts.examples.geant4.Geant4Detector.Config()
    g4DetectorCfg.name = trackingGeometryName
    g4DetectorCfg.protoDetector = protoDetector
    g4DetectorCfg.g4SurfaceOptions = g4SurfaceOptions
    g4DetectorCfg.g4World = g4World
    g4DetectorCfg.logLevel = logLevel

    return acts.examples.geant4.Geant4Detector().constructTrackingGeometry(
        g4DetectorCfg
    )


parser = argparse.ArgumentParser()
parser.add_argument("gdml")
args = parser.parse_args()

trackingGeometry, decorators, detectorElements = trackingGeometryFromGDML(
    "odd-light.gdml",
    "odd-light-proto-detector.json",
    "odd-light",
    ["sens_vol"],
    ["pass_vol"],
)

svgWriterConfig = acts.examples.SvgTrackingGeometryWriter.Config()
svgWriterConfig.outputDir = "svgs"
svgWriter = acts.examples.SvgTrackingGeometryWriter(
    config=svgWriterConfig, level=acts.logging.INFO
)

eventStore = acts.examples.WhiteBoard(name="EventStore#0", level=acts.logging.INFO)

context = acts.examples.AlgorithmContext(0, 0, eventStore)
svgWriter.write(context, trackingGeometry)
