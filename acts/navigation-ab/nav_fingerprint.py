#!/usr/bin/env python3
"""Write a propagation summary for the ODD in Gen1 or Gen3.

Diff the resulting ROOT files between two builds to see whether navigation
changed.
"""

import argparse

import acts
import acts.examples
import acts.examples.root
from acts.examples.odd import getOpenDataDetector
from acts.examples.simulation import (
    addParticleGun,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    MomentumConfig,
)

u = acts.UnitConstants


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--geo-mode", choices=["gen1", "gen3"], default="gen3")
    p.add_argument("-n", "--events", type=int, default=20)
    p.add_argument("--tracks", type=int, default=20)
    p.add_argument("-s", "--seed", type=int, default=221177)
    p.add_argument("-o", "--output", required=True)
    args = p.parse_args()

    gen3 = args.geo_mode == "gen3"
    rnd = acts.examples.RandomNumbers(seed=args.seed)

    s = acts.examples.Sequencer(
        events=args.events, numThreads=1, logLevel=acts.logging.WARNING
    )

    addParticleGun(
        s,
        ParticleConfig(
            num=args.tracks, pdg=acts.PdgParticle.eMuon, randomizeCharge=True
        ),
        EtaConfig(-2.5, 2.5, uniform=True),
        PhiConfig(0.0, 360.0 * u.degree),
        MomentumConfig(0.5 * u.GeV, 10.0 * u.GeV, transverse=True),
        rnd=rnd,
    )

    with getOpenDataDetector(gen3=gen3) as detector:
        trackingGeometry = detector.trackingGeometry()

        navigator = acts.Navigator(trackingGeometry=trackingGeometry)
        propagator = acts.Propagator(acts.StraightLineStepper(), navigator)
        propagatorImpl = acts.examples.ConcretePropagator(propagator)

        s.addAlgorithm(
            acts.examples.ParticleTrackParamExtractor(
                level=acts.logging.WARNING,
                inputParticles="particles_generated",
                outputTrackParameters="start_parameters",
            )
        )
        s.addAlgorithm(
            acts.examples.PropagationAlgorithm(
                propagatorImpl=propagatorImpl,
                level=acts.logging.WARNING,
                sterileLogger=False,
                inputTrackParameters="start_parameters",
                outputSummaryCollection="propagation_summary",
                outputMaterialCollection="material_tracks",
            )
        )
        s.addWriter(
            acts.examples.root.RootPropagationSummaryWriter(
                level=acts.logging.WARNING,
                inputSummaryCollection="propagation_summary",
                filePath=args.output,
            )
        )

        s.run()


if __name__ == "__main__":
    main()
