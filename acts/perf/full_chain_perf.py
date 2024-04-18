#!/usr/bin/env python3

from pathlib import Path

import acts
import acts.examples
from acts.examples.simulation import (
    addPythia8,
    addParticleGun,
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    addFatras,
    ParticleSelectorConfig,
    addDigitization,
)
from acts.examples.reconstruction import (
    addSeeding,
    TrackSelectorConfig,
    CkfConfig,
    addCKFTracks,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("outputDir", help="Output directory", type=Path)
parser.add_argument("--ttbar", help="Use ttbar events", action="store_true")
args = parser.parse_args()

u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
outputDir = Path.cwd() / args.outputDir
outputDir.mkdir(parents=True, exist_ok=True)
# acts.examples.dump_args_calls(locals())  # show python binding calls

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(
    odd_dir=geoDir, mdecorator=oddMaterialDeco
)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)


events = 20
runs = 50

if args.ttbar:
    events = 3
    runs = 10


def create_sequencer():
    s = acts.examples.Sequencer(
        events=events,
        numThreads=1,
        outputDir=str(outputDir),
        trackFpes=False,
        # logLevel=acts.logging.WARNING,
    )

    if not args.ttbar:
        addParticleGun(
            s,
            MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, transverse=True),
            EtaConfig(-3.0, 3.0),
            PhiConfig(0.0, 360.0 * u.degree),
            ParticleConfig(4, acts.PdgParticle.eMuon, randomizeCharge=True),
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(
                    0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 1.0 * u.ns
                ),
            ),
            multiplicity=50,
            rnd=rnd,
            # outputDirRoot=outputDir,
            # outputDirCsv=outputDir,
        )
    else:
        addPythia8(
            s,
            hardProcess=["Top:qqbar2ttbar=on"],
            npileup=200,
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(
                    0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns
                ),
            ),
            rnd=rnd,
            # outputDirRoot=outputDir,
            # outputDirCsv=outputDir,
        )

    addFatras(
        s,
        trackingGeometry,
        field,
        preSelectParticles=ParticleSelectorConfig(
            rho=(0.0, 24 * u.mm),
            absZ=(0.0, 1.0 * u.m),
            eta=(-3.0, 3.0),
            pt=(150 * u.MeV, None),
            removeNeutral=True,
        ),
        enableInteractions=True,
        # outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
        rnd=rnd,
    )

    addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=oddDigiConfig,
        # outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
        rnd=rnd,
    )

    addSeeding(
        s,
        trackingGeometry,
        field,
        geoSelectionConfigFile=oddSeedingSel,
        # outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
    )

    addCKFTracks(
        s,
        trackingGeometry,
        field,
        TrackSelectorConfig(
            pt=(1.0 * u.GeV, None),
            absEta=(None, 3.0),
            loc0=(-4.0 * u.mm, 4.0 * u.mm),
            nMeasurementsMin=7,
            maxHoles=2,
            maxOutliers=2,
        ),
        CkfConfig(
            seedDeduplication=True,
            stayOnSeed=True,
        ),
        # writeCovMat=True,
        # outputDirCsv=outputDir,
        # outputDirRoot=outputDir,
        # logLevel=acts.logging.VERBOSE,
    )

    return s


import pandas as pd

s = create_sequencer()

times = []
for i in range(runs):
    print(f"start round {i}")
    s.run()
    d = pd.read_csv(outputDir / "timing.tsv", sep="\t")
    t = {
        "fatras": d[d["identifier"] == "Algorithm:FatrasSimulation"][
            "time_perevent_s"
        ].values[0],
        "ckf": d[d["identifier"] == "Algorithm:TrackFindingAlgorithm"][
            "time_perevent_s"
        ].values[0],
    }
    print(f"finished and got times {t}")
    times.append(t)
    pd.DataFrame(times).to_csv(outputDir / "times.csv", index=False)
