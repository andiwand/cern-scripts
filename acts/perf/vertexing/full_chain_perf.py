#!/usr/bin/env python3

from pathlib import Path

import acts
import acts.examples
from acts.examples.simulation import (
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    addParticleGun,
    addPythia8,
    ParticleSelectorConfig,
    addFatras,
    addGeant4,
    addDigitization,
)
from acts.examples.reconstruction import (
    SeedFinderConfigArg,
    addSeeding,
    TrackSelectorConfig,
    CkfConfig,
    addCKFTracks,
    addVertexFitting,
    VertexFinder,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("outputDir", help="Output directory", type=Path)
parser.add_argument("--ttbar", help="Use ttbar events", action="store_true")
parser.add_argument("--geant4", help="Use geant4 simulation", action="store_true")
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


events = 20 if not args.ttbar else 5
runs = 50 if not args.ttbar else 10
pus = [0, 60, 120, 200, 300]

vertexingVariants = [
    {
        "name": "amvf_gauss",
        "seeder": acts.VertexSeedFinder.GaussianSeeder,
        "useTime": False,
    },
    {
        "name": "amvf_grid_sparse",
        "seeder": acts.VertexSeedFinder.SparseGridSeeder,
        "useTime": False,
    },
    {
        "name": "amvf_grid_adaptive",
        "seeder": acts.VertexSeedFinder.AdaptiveGridSeeder,
        "useTime": False,
    },
    {
        "name": "amvf_grid_sparse_time",
        "seeder": acts.VertexSeedFinder.SparseGridSeeder,
        "useTime": True,
    },
]


def create_sequencer(ttbar: bool, pu: int, geant4: bool):
    s = acts.examples.Sequencer(
        events=events,
        numThreads=1,
        outputDir=str(outputDir),
        trackFpes=False,
        # logLevel=acts.logging.WARNING,
    )

    if not ttbar:
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
            multiplicity=1 + pu,
            rnd=rnd,
            # outputDirRoot=outputDir,
            # outputDirCsv=outputDir,
        )
    else:
        addPythia8(
            s,
            hardProcess=["Top:qqbar2ttbar=on"],
            npileup=pu,
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

    if not geant4:
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
    else:
        addGeant4(
            s,
            detector,
            trackingGeometry,
            field,
            preSelectParticles=ParticleSelectorConfig(
                rho=(0.0, 24 * u.mm),
                absZ=(0.0, 1.0 * u.m),
                eta=(-3.0, 3.0),
                pt=(150 * u.MeV, None),
                removeNeutral=True,
            ),
            outputDirRoot=outputDir,
            # outputDirCsv=outputDir,
            rnd=rnd,
            killVolume=trackingGeometry.worldVolume,
            killAfterTime=25 * u.ns,
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
        seedFinderConfigArg=SeedFinderConfigArg(
            # r=(33 * u.mm, 200 * u.mm),
            # deltaR=(1 * u.mm, 60 * u.mm),
            # collisionRegion=(-250 * u.mm, 250 * u.mm),
            # z=(-2000 * u.mm, 2000 * u.mm),
            # maxSeedsPerSpM=1,
            # sigmaScattering=5,
            # radLengthPerSeed=0.1,
            minPt=0.9 * u.GeV,
            # impactMax=3 * u.mm,
        ),
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
            chi2CutOff=15,
            numMeasurementsCutOff=1,
            seedDeduplication=True,
            stayOnSeed=True,
        ),
        # writeCovMat=True,
        # outputDirCsv=outputDir,
        # outputDirRoot=outputDir,
        # logLevel=acts.logging.VERBOSE,
    )

    s.addAlgorithm(
        acts.examples.TracksToParameters(
            level=acts.logging.INFO,
            inputTracks="tracks",
            outputTrackParameters="trackParameters",
        )
    )

    for variant in vertexingVariants:
        path = outputDir / f"pu{pu}" / variant["name"]
        path.mkdir(parents=True, exist_ok=True)
        addVertexFitting(
            s,
            field,
            trackParameters="trackParameters",
            outputProtoVertices=f"{variant['name']}_protovertices",
            outputVertices=f"{variant['name']}_fittedVertices",
            vertexFinder=VertexFinder.AMVF,
            seeder=variant["seeder"],
            useTime=variant["useTime"],
            outputDirRoot=path,
        )

    return s


import itertools
import pandas as pd
import uproot as up
import awkward as ak

times = []
for pu, run in itertools.product(pus, range(runs)):
    print(f"start round {run}")

    s = create_sequencer(args.ttbar, pu, args.geant4)
    s.run()

    timing = pd.read_csv(outputDir / "timing.tsv", sep="\t")

    def get_time_per_event(d, algorithm, index):
        return d[d["identifier"] == algorithm]["time_perevent_s"].values[index]

    t = {
        "pu": pu,
        "ckf": get_time_per_event(timing, "Algorithm:TrackFindingAlgorithm", 0),
    }
    if not args.geant4:
        t["fatras"] = get_time_per_event(timing, "Algorithm:FatrasSimulation", 0)
    else:
        t["geant4"] = get_time_per_event(timing, "Algorithm:Geant4Simulation", 0)
    for i, variant in enumerate(vertexingVariants):
        t[variant["name"]] = get_time_per_event(
            timing, "Algorithm:AdaptiveMultiVertexFinder", i
        )
    print(f"finished and got times {t}")
    times.append(t)

    times_summarized = pd.DataFrame(times)
    times_summarized.to_csv(outputDir / "times.csv", index=False)

    # summerize the results

    def get_vertex_perf(pu, variant):
        path = outputDir / f"pu{pu}" / variant["name"] / "performance_vertexing.root"
        columns = [
            "event_nr",
            "nRecoVtx",
            "nTrueVtx",
            "nCleanVtx",
            "nMergedVtx",
            "nSplitVtx",
        ]
        if not path.exists():
            return pd.DataFrame(columns=columns)
        return ak.to_dataframe(
            up.open(path)["vertexing"].arrays(
                columns,
                library="ak",
            ),
            how="outer",
        ).dropna()

    summary = [
        {
            "pu": pu,
            "vtxName": variant["name"],
            "vtxTime_mean": times_summarized[times_summarized["pu"] == pu].mean()[
                variant["name"]
            ],
            "nCleanVtx_mean": get_vertex_perf(pu, variant).mean()["nCleanVtx"],
        }
        for pu in pus
        for variant in vertexingVariants
    ]

    pd.DataFrame(summary).to_csv(outputDir / "summary.csv", index=False)
