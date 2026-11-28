#!/usr/bin/env python3
"""ODD pu200 simulation and geometric digitization only, for the occupancy."""

import argparse
import pathlib

import acts
import acts.examples
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addPythia8,
    addGenParticleSelection,
    addFatras,
    addGeant4,
    addDigitization,
)

u = acts.UnitConstants

p = argparse.ArgumentParser()
p.add_argument("--output", type=pathlib.Path, required=True)
p.add_argument("--events", type=int, default=5)
p.add_argument("--pu", type=int, default=200)
p.add_argument("--process", default="SoftQCD:all = on")
p.add_argument("--pmin", type=float, default=0.5, help="Fatras pMin in GeV")
p.add_argument("--geant4", action="store_true")
args = p.parse_args()

geoDir = getOpenDataDetectorDirectory()
cfgDir = pathlib.Path("/Users/andreas/cern/source/acts/acts/dev3/Examples/Configs")
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
s = acts.examples.Sequencer(events=args.events, numThreads=1, outputDir=str(out), trackFpes=False)
for d in detector.contextDecorators():
    s.addContextDecorator(d)

addPythia8(
    s,
    hardProcess=["Top:qqbar2ttbar=on"],
    npileup=args.pu,
    pileupProcess=[args.process],
    vtxGen=acts.examples.GaussianVertexGenerator(
        mean=acts.Vector4(0, 0, 0, 0),
        stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns),
    ),
    rnd=rnd,
)
addGenParticleSelection(
    s, ParticleSelectorConfig(rho=(0.0, 24 * u.mm), absZ=(0.0, 1.0 * u.m))
)
if args.geant4:
    addGeant4(
        s, detector, trackingGeometry, field, rnd=rnd, outputDirRoot=out,
        killVolume=trackingGeometry.highestTrackingVolume, killAfterTime=25 * u.ns,
    )
else:
    addFatras(
        s, trackingGeometry, field, enableInteractions=True,
        pMin=args.pmin * u.GeV, outputDirRoot=out, rnd=rnd,
    )
addDigitization(
    s, trackingGeometry, field,
    digiConfigFile=cfgDir / "odd-digi-geometric-config.json",
    doMerge=True, mergeCommonCorner=True, outputDirRoot=out, rnd=rnd,
)
s.run()
