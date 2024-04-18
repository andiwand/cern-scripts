#!/usr/bin/env python3

import acts
import acts.examples.geant4 as actsG4


def trackingGeometryFromGDML(
    gdmlFile,
    protoFile,
    trackingGeometryName,
    sensitiveTags,
    passiveTags,
    logLevel=acts.logging.VERBOSE,
):
    print("odd-light: TrackingGeometry construction")

    print("odd-light: Building Geant4 detector & extract world volume")
    g4DetectorConstruction = actsG4.GdmlDetectorConstruction(gdmlFile)
    g4World = g4DetectorConstruction.Construct()

    print("odd-light: Reading ProtoDetector description")
    protoDetector = acts.examples.ProtoDetector(protoFile)

    print("odd-light: Preparing and performing the conversion")
    g4SensitiveSelector = actsG4.VolumeNameSelector(sensitiveTags, False)
    g4PassiveSelector = actsG4.VolumeNameSelector(passiveTags, False)

    g4SurfaceOptions = actsG4.SurfaceFactoryOptions()
    g4SurfaceOptions.sensitiveSurfaceSelector = g4SensitiveSelector
    g4SurfaceOptions.passiveSurfaceSelector = g4PassiveSelector

    g4DetectorCfg = actsG4.Geant4Detector.Config()
    g4DetectorCfg.name = trackingGeometryName
    g4DetectorCfg.protoDetector = protoDetector
    g4DetectorCfg.g4SurfaceOptions = g4SurfaceOptions
    g4DetectorCfg.g4World = g4World
    g4DetectorCfg.logLevel = logLevel

    return actsG4.Geant4Detector().constructTrackingGeometry(g4DetectorCfg)


if "__main__" == __name__:
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
