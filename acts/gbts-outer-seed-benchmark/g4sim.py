#!/usr/bin/env python3
"""ODD ttbar + pile-up with Geant4: write particles with hits and sim hits."""

import argparse
import pathlib

import acts
import acts.examples
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addPythia8,
    addGenParticleSelection,
    addGeant4,
)

u = acts.UnitConstants

p = argparse.ArgumentParser()
p.add_argument("--output", type=pathlib.Path, required=True)
p.add_argument("--events", type=int, default=5)
p.add_argument("--skip", type=int, default=0)
p.add_argument("--pu", type=int, default=200)
args = p.parse_args()

geoDir = getOpenDataDetectorDirectory()
detector = getOpenDataDetector(
    odd_dir=geoDir,
    materialDecorator=acts.IMaterialDecorator.fromFile(
        geoDir / "data/odd-material-maps.root"
    ),
)
trackingGeometry = detector.trackingGeometry()
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

out = args.output
out.mkdir(parents=True, exist_ok=True)
s = acts.examples.Sequencer(
    events=args.events, skip=args.skip, numThreads=1, outputDir=str(out),
    trackFpes=False,
)
for d in detector.contextDecorators():
    s.addContextDecorator(d)

addPythia8(
    s,
    hardProcess=["Top:qqbar2ttbar=on"],
    npileup=args.pu,
    pileupProcess=["SoftQCD:inelastic = on"],
    vtxGen=acts.examples.GaussianVertexGenerator(
        mean=acts.Vector4(0, 0, 0, 0),
        stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns),
    ),
    rnd=rnd,
)
addGenParticleSelection(
    s, ParticleSelectorConfig(rho=(0.0, 24 * u.mm), absZ=(0.0, 1.0 * u.m))
)
addGeant4(
    s, detector, trackingGeometry, field, rnd=rnd, outputDirRoot=out,
    keepParticlesWithoutHits=False,
    killVolume=trackingGeometry.highestTrackingVolume, killAfterTime=25 * u.ns,
)
s.run()
