#!/usr/bin/env python3
import pathlib, acts, acts.examples
from acts.examples.reconstruction import (
    TrackSelectorRanges,
    addVertexFitting,
    VertexFinder,
)

u = acts.UnitConstants
outputDir = pathlib.Path.cwd() / "output"

field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))

s = acts.examples.Sequencer(events=1, numThreads=1, outputDir=str(outputDir))

s.addReader(
    acts.examples.CsvTrackParameterReader(
        inputDir="./csv",
        inputStem="tracks",
        outputTrackParameters="trackParameters",
        beamspot=[0, 0, 0],
        level=acts.logging.Level.VERBOSE,
    )
)

addVertexFitting(
    s,
    field,
    trajectories=None,
    trackParameters="trackParameters",
    vertexFinder=VertexFinder.Iterative,
    logLevel=acts.logging.Level.VERBOSE,
)

s.run()
