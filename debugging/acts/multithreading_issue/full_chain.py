#!/usr/bin/env python3
from pathlib import Path
import argparse
import tempfile
import shutil
import datetime
import sys
import subprocess

# this has to happen before we import the ACTS module
import acts.examples

# @TODO: Fix failure in gain matrix smoothing
# See https://github.com/acts-project/acts/issues/1215
acts.logging.setFailureThreshold(acts.logging.FATAL)

from truth_tracking_kalman import runTruthTrackingKalman
from truth_tracking_gsf import runTruthTrackingGsf
from common import getOpenDataDetectorDirectory
from acts.examples.odd import getOpenDataDetector
from acts.examples.simulation import (
    addParticleGun,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    addFatras,
    addDigitization,
)
from acts.examples.reconstruction import (
    addSeeding,
    TruthSeedRanges,
    ParticleSmearingSigmas,
    SeedFinderConfigArg,
    SeedFinderOptionsArg,
    SeedingAlgorithm,
    TrackParamsEstimationConfig,
    addCKFTracks,
    CKFPerformanceConfig,
    addAmbiguityResolution,
    AmbiguityResolutionConfig,
    addVertexFitting,
    VertexFinder,
    TrackSelectorRanges,
)

outdir = Path("./output")
outdir.mkdir(exist_ok=True)


srcdir = Path(__file__).resolve().parent.parent.parent
geoDir = getOpenDataDetectorDirectory()


u = acts.UnitConstants

oddMaterialMap = geoDir / "data/odd-material-maps.root"
matDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(geoDir, mdecorator=matDeco)
digiConfig = geoDir / "config/odd-digi-smearing-config.json"
geoSel = geoDir / "config/odd-seeding-config.json"


field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))

# TODO There seems to be a difference to the reference files when using
# multithreading ActsAnalysisResidualsAndPulls
s = acts.examples.Sequencer(
    events=500,
    numThreads=1,
    logLevel=acts.logging.INFO,
)

for d in decorators:
    s.addContextDecorator(d)

rnd = acts.examples.RandomNumbers(seed=42)

vtxGen = acts.examples.GaussianVertexGenerator(
    stddev=acts.Vector4(10 * u.um, 10 * u.um, 50 * u.mm, 0),
    mean=acts.Vector4(0, 0, 0, 0),
)

addParticleGun(
    s,
    EtaConfig(-4.0, 4.0),
    ParticleConfig(4, acts.PdgParticle.eMuon, True),
    PhiConfig(0.0, 360.0 * u.degree),
    vtxGen=vtxGen,
    multiplicity=1,
    rnd=rnd,
)

addFatras(
    s,
    trackingGeometry,
    field,
    rnd=rnd,
)

addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=digiConfig,
    rnd=rnd,
)

addSeeding(
    s,
    trackingGeometry,
    field,
    TruthSeedRanges(pt=(500.0 * u.MeV, None), nHits=(9, None)),
    ParticleSmearingSigmas(pRel=0.01),  # only used by SeedingAlgorithm.TruthSmeared
    SeedFinderConfigArg(
        r=(None, 200 * u.mm),  # rMin=default, 33mm
        deltaR=(1 * u.mm, 60 * u.mm),
        collisionRegion=(-250 * u.mm, 250 * u.mm),
        z=(-2000 * u.mm, 2000 * u.mm),
        maxSeedsPerSpM=1,
        sigmaScattering=5,
        radLengthPerSeed=0.1,
        minPt=500 * u.MeV,
        impactMax=3 * u.mm,
    ),
    SeedFinderOptionsArg(bFieldInZ=1.99724 * u.T, beamPos=(0.0, 0.0)),
    TrackParamsEstimationConfig(deltaR=(10.0 * u.mm, None)),
    seedingAlgorithm=SeedingAlgorithm.Default,
    geoSelectionConfigFile=geoSel,
    rnd=rnd,  # only used by SeedingAlgorithm.TruthSmeared
    outputDirRoot=outdir,
)

addCKFTracks(
    s,
    trackingGeometry,
    field,
    CKFPerformanceConfig(ptMin=400.0 * u.MeV, nMeasurementsMin=6),
    TrackSelectorRanges(
        removeNeutral=True,
        loc0=(None, 4.0 * u.mm),
        pt=(500 * u.MeV, None),
    ),
    outputDirRoot=outdir,
    outputDirCsv=None,
)

s.run()
