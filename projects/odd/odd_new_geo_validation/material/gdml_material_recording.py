#!/usr/bin/env python3

import os

import acts
from acts.examples import (
    GaussianVertexGenerator,
    ParametricParticleGenerator,
    FixedMultiplicityGenerator,
    EventGenerator,
    RandomNumbers,
)

import acts.examples.geant4


u = acts.UnitConstants


def runMaterialRecording(g4geo, outputDir, tracksPerEvent=100, s=None):
    rnd = RandomNumbers(seed=228)

    s = s or acts.examples.Sequencer(events=1000, numThreads=1)

    evGen = EventGenerator(
        level=acts.logging.INFO,
        generators=[
            EventGenerator.Generator(
                multiplicity=FixedMultiplicityGenerator(n=1),
                vertex=GaussianVertexGenerator(
                    stddev=acts.Vector4(0, 0, 0, 0),
                    mean=acts.Vector4(0, 0, 0, 0),
                ),
                particles=ParametricParticleGenerator(
                    p=(10 * u.GeV, 10 * u.GeV),
                    phi=(0 * u.degree, 360 * u.degree),
                    eta=(-4, 4),
                    numParticles=tracksPerEvent,
                    etaUniform=True,
                ),
            )
        ],
        outputParticles="particles_initial",
        randomNumbers=rnd,
    )

    s.addReader(evGen)

    g4AlgCfg = acts.examples.geant4.materialRecordingConfig(
        level=acts.logging.INFO,
        detector=g4geo,
        inputParticles=evGen.config.outputParticles,
        outputMaterialTracks="material_tracks",
        randomNumbers=rnd,
    )

    g4AlgCfg.detectorConstruction = g4geo

    g4Alg = acts.examples.geant4.Geant4Simulation(
        level=acts.logging.INFO,
        config=g4AlgCfg,
    )

    s.addAlgorithm(g4Alg)

    s.addWriter(
        acts.examples.RootMaterialTrackWriter(
            prePostStep=True,
            recalculateTotals=True,
            collapseInteractions=True,
            collection="material_tracks",
            filePath=os.path.join(outputDir, "geant4_material_tracks.root"),
            level=acts.logging.INFO,
        )
    )

    return s


if "__main__" == __name__:
    g4geo = acts.examples.geant4.GdmlDetectorConstruction("odd-light.gdml")

    runMaterialRecording(g4geo=g4geo, tracksPerEvent=100, outputDir=os.getcwd()).run()
