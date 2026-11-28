#!/usr/bin/env python3
"""GBTS seed fit position and CKF direction: every variant on the same ODD events."""

import argparse
import pathlib

import acts
import acts.examples
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory
from acts.examples.simulation import (
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    ParticleSelectorConfig,
    addParticleGun,
    addPythia8,
    addGenParticleSelection,
    addFatras,
    addSimParticleSelection,
    addDigitization,
    addDigiParticleSelection,
)
from acts.examples.reconstruction import (
    addTrackWriters,
    addSeeding,
    SeedingAlgorithm,
    GbtsConfigArg,
    CkfConfig,
    addCKFTracks,
    TrackSelectorConfig,
    addAmbiguityResolution,
    AmbiguityResolutionConfig,
)

u = acts.UnitConstants

# <start end>_<direction of the first CKF pass>. The GBTS fit and the seed
# surface are at the start end.
VARIANTS = {
    "inner_outward": dict(outer=False),
    "outer_outward": dict(outer=True),
    "outer_inward": dict(outer=True, reverse=True),
    "inner_outward_stay": dict(outer=False, stay=True),
    "outer_outward_notrim": dict(outer=True, trim=False),
    "outer_inward_notrim": dict(outer=True, reverse=True, trim=False),
}
for name in list(VARIANTS):
    if not name.endswith(("_stay", "_notrim")):
        VARIANTS[f"{name}_chi30"] = VARIANTS[name] | dict(chi2=(30.0, 50.0))

p = argparse.ArgumentParser()
p.add_argument("--output", type=pathlib.Path, required=True)
p.add_argument("--events", type=int, default=100)
p.add_argument("--jobs", type=int, default=-1)
p.add_argument("--ttbar", action="store_true")
p.add_argument("--pu", type=int, default=0)
p.add_argument("--muons", type=int, default=1, help="muons per event")
p.add_argument("--variants", nargs="+", default=list(VARIANTS))
p.add_argument("--hits", action="store_true", help="write simhits")
p.add_argument("--digi", choices=["smearing", "geometric"], default="smearing")
p.add_argument("--input", type=pathlib.Path, help="read particles and sim hits from ROOT")
args = p.parse_args()

geoDir = getOpenDataDetectorDirectory()
actsDir = pathlib.Path(acts.__file__).resolve()
actsDir = pathlib.Path("/Users/andreas/cern/source/acts/acts/dev3")
cfgDir = actsDir / "Examples/Configs"

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
    events=args.events,
    numThreads=args.jobs,
    outputDir=str(out),
    trackFpes=False,
)
for d in detector.contextDecorators():
    s.addContextDecorator(d)

if args.input is not None:
    import acts.examples.root

    s.addReader(
        acts.examples.root.RootParticleReader(
            level=acts.logging.INFO,
            filePath=str(args.input / "particles_simulation.root"),
            outputParticles="particles_simulated",
        )
    )
    s.addWhiteboardAlias("particles", "particles_simulated")
    s.addReader(
        acts.examples.root.RootSimHitReader(
            level=acts.logging.INFO,
            filePath=str(args.input / "hits.root"),
            outputSimHits="simhits",
        )
    )
    addSimParticleSelection(
        s,
        ParticleSelectorConfig(
            rho=(0.0, 24 * u.mm), absZ=(0.0, 1.0 * u.m), removeNeutral=True
        ),
    )
else:
    if args.ttbar:
        addPythia8(
            s,
            hardProcess=["Top:qqbar2ttbar=on"],
            npileup=args.pu,
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns),
            ),
            rnd=rnd,
            outputDirRoot=None,
        )
        addGenParticleSelection(
            s,
            ParticleSelectorConfig(
                rho=(0.0, 24 * u.mm),
                absZ=(0.0, 1.0 * u.m),
            ),
        )
    else:
        addParticleGun(
            s,
            MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, transverse=True),
            EtaConfig(-3.0, 3.0, uniform=True),
            PhiConfig(0.0, 360.0 * u.degree),
            ParticleConfig(args.muons, acts.PdgParticle.eMuon, randomizeCharge=True),
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 1.0 * u.ns),
            ),
            multiplicity=1,
            rnd=rnd,
        )

    addFatras(
        s,
        trackingGeometry,
        field,
        enableInteractions=True,
        outputDirRoot=out if args.hits else None,
        rnd=rnd,
    )
    if args.ttbar:
        addSimParticleSelection(
            s,
            ParticleSelectorConfig(
                rho=(0.0, 24 * u.mm), absZ=(0.0, 1.0 * u.m), removeNeutral=True
            ),
        )

addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=cfgDir / f"odd-digi-{args.digi}-config.json",
    doMerge=True,
    mergeCommonCorner=True,
    rnd=rnd,
)

addDigiParticleSelection(
    s,
    ParticleSelectorConfig(
        pt=(1.0 * u.GeV, None),
        eta=(-3.0, 3.0),
        measurements=(9, None),
        removeNeutral=True,
    ),
)

for name in args.variants:
    v = VARIANTS[name]
    prefix = f"{name}_"
    vout = out / name
    vout.mkdir(exist_ok=True)
    s.addWhiteboardAlias(f"{prefix}measurement_subset", "measurement_subset")

    addSeeding(
        s,
        trackingGeometry,
        field,
        seedingAlgorithm=SeedingAlgorithm.Gbts,
        layerMappingConfigFile=cfgDir / "odd-gbts-layer-map.json",
        connectorInputConfigFile=cfgDir / "odd-gbts-connection-table.json",
        gbtsConfigArg=GbtsConfigArg(
            seederConfig=acts.examples.GraphBasedSeedingConfig(
                minSeedLevel=2,
                seedFitAtOutermost=v["outer"],
            ),
            graphConfig=acts.examples.GbtsGraphBuilderConfig(
                minPt=0.9 * u.GeV,
                z0HistogramMaxBarrelOrder=-1,
            ),
            useAdaptiveCuts=False,
        ),
        gbtsSeedParameters=True,
        paramEstimationSpacePoints=acts.examples.SeedSpacePointSelection.SpreadTriplet,
        paramEstimationOnLastSpacePoint=v["outer"],
        initialSigmas=[
            1 * u.mm,
            1 * u.mm,
            1 * u.degree,
            1 * u.degree,
            0 * u.e / u.GeV,
            1 * u.ns,
        ],
        initialSigmaQoverPt=0.1 * u.e / u.GeV,
        initialSigmaPtRel=0.1,
        initialVarInflation=[1.0] * 6,
        particleHypothesis=acts.ParticleHypothesis.muon,
        geoSelectionConfigFile=cfgDir / "odd-seeding-config.json",
        outputDirRoot=vout,
        trackParameterPerformance=True,
        prefix=prefix,
    )

    if name == args.variants[0]:
        # the seeds themselves, matched by majority so impure seeds keep a
        # particle. the writers read the `track_particle_matching` alias
        s.addAlgorithm(
            acts.examples.TrackTruthMatcher(
                level=acts.logging.INFO,
                inputTracks=f"{prefix}seed-tracks",
                inputParticles="particles_selected",
                inputMeasurementParticlesMap="measurement_particles_map",
                outputTrackParticleMatching=f"{prefix}seed_majority_matching",
                outputParticleTrackMatching=f"{prefix}majority_seed_matching",
                matchingRatio=0.5,
                doubleMatching=False,
            )
        )
        s.addWhiteboardAlias(
            "track_particle_matching", f"{prefix}seed_majority_matching"
        )
        addTrackWriters(
            s,
            name="seeds",
            tracks=f"{prefix}seed-tracks",
            outputDirRoot=out,
            writeStates=True,
        )

    addCKFTracks(
        s,
        trackingGeometry,
        field,
        TrackSelectorConfig(
            pt=(1.0 * u.GeV if args.ttbar else 0.0, None),
            absEta=(None, 3.0),
            loc0=(-4.0 * u.mm, 4.0 * u.mm),
            nMeasurementsMin=7,
            maxHoles=2,
            maxOutliers=2,
        ),
        CkfConfig(
            chi2CutOffMeasurement=v.get("chi2", (15.0, 25.0))[0],
            chi2CutOffOutlier=v.get("chi2", (15.0, 25.0))[1],
            numMeasurementsCutOff=2,
            seedDeduplication=True,
            stayOnSeed=v.get("stay", False),
            trimTracks=v.get("trim", True),
            pixelVolumes=[16, 17, 18],
            stripVolumes=[23, 24, 25],
            maxPixelHoles=1,
            maxStripHoles=2,
            constrainToVolumes=[2, 32, 4, 16, 17, 18, 20, 23, 24, 25, 26, 8, 28, 29, 30],
        ),
        outputDirRoot=vout,
        writeCovMat=True,
        writeTrackStates=True,
        reverseSearch=v.get("reverse", False),
        prefix=prefix,
    )

    addAmbiguityResolution(
        s,
        AmbiguityResolutionConfig(
            maximumSharedHits=3, maximumIterations=1000000, nMeasurementsMin=7
        ),
        outputDirRoot=vout,
        writeCovMat=True,
        writeTrackStates=True,
        prefix=prefix,
    )

s.run()
