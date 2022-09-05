#!/usr/bin/env python3

import acts
from acts.examples import Sequencer, RootMaterialTrackWriter

import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], ".."))
import gdml_geometry


u = acts.UnitConstants


def runMaterialValidation(
    trackingGeometry,
    decorators,
    outputDir,
    s=None,
):
    rnd = acts.examples.RandomNumbers(seed=42)

    s = s or Sequencer(events=1000, numThreads=-1)

    for decorator in decorators:
        s.addContextDecorator(decorator)

    nav = acts.Navigator(trackingGeometry=trackingGeometry)

    stepper = acts.StraightLineStepper()

    prop = acts.examples.ConcretePropagator(acts.Propagator(stepper, nav))

    alg = acts.examples.PropagationAlgorithm(
        propagatorImpl=prop,
        level=acts.logging.INFO,
        randomNumberSvc=rnd,
        ntests=1000,
        sterileLogger=True,
        propagationStepCollection="propagation-steps",
        propagationMaterialCollection="material_tracks",
        energyLoss=False,
        multipleScattering=False,
        recordMaterialInteractions=True,
        phiRange=(0 * u.degree, 360 * u.degree),
        etaRange=(-4, 4),
        ptRange=(10 * u.GeV, 10 * u.GeV),
        d0Sigma=0,
        z0Sigma=0,
        phiSigma=0,
        thetaSigma=0,
        qpSigma=0,
        tSigma=0,
    )

    s.addAlgorithm(alg)

    s.addWriter(
        RootMaterialTrackWriter(
            prePostStep=True,
            recalculateTotals=True,
            collapseInteractions=False,
            collection=alg.config.propagationMaterialCollection,
            filePath=os.path.join(outputDir, "acts_material_tracks.root"),
            level=acts.logging.INFO,
        )
    )

    return s


if "__main__" == __name__:
    (
        trackingGeometry,
        decorators,
        detectorElements,
    ) = gdml_geometry.trackingGeometryFromGDML(
        "odd-light.gdml",
        "odd-light-proto-detector.json",
        "odd-light",
        ["sens_vol"],
        ["pass_vol"],
    )

    runMaterialValidation(trackingGeometry, decorators, outputDir=os.getcwd()).run()
