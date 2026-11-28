#!/usr/bin/env python3
"""Paired ODD ttbar study: generate/digitize/seed once, reconstruct each variant."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import acts
import acts.examples as ex
from acts.examples.odd import getOpenDataDetector
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addPythia8,
    addGenParticleSelection,
    addFatras,
    addDigitization,
    addDigiParticleSelection,
)
from acts.examples.reconstruction import addSeeding
from acts.examples.root import (
    RootTrackSummaryWriter,
    RootPatternRecognitionPerformanceWriter,
)

p = argparse.ArgumentParser()
p.add_argument("--output", type=Path, required=True)
p.add_argument("--events", type=int, default=20)
p.add_argument("--pu", type=int, default=400)
p.add_argument("--skip", type=int, default=0)
p.add_argument("--variants", nargs="+", default=["core15", "core25", "tail"])
p.add_argument(
    "--source", type=Path, default=Path.home() / "cern/source/acts/acts/dev3"
)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
u = acts.UnitConstants
level = acts.logging.WARNING
detector = getOpenDataDetector(logLevel=level, buildCalorimeter=False)
geometry = detector.trackingGeometry()
field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))
rnd = ex.RandomNumbers(seed=42)
s = ex.Sequencer(
    events=a.events,
    skip=a.skip,
    numThreads=1,
    outputDir=str(a.output),
    trackFpes=False,
    logLevel=level,
)

addPythia8(
    s,
    hardProcess=["Top:qqbar2ttbar=on"],
    npileup=a.pu,
    pileupProcess=["SoftQCD:all=on"],
    rnd=rnd,
    vtxGen=ex.GaussianVertexGenerator(
        mean=acts.Vector4(0, 0, 0, 0),
        stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5 * u.ns),
    ),
)
addGenParticleSelection(
    s,
    ParticleSelectorConfig(
        rho=(0, 24 * u.mm), absZ=(0, 1 * u.m), eta=(-3, 3), pt=(150 * u.MeV, None)
    ),
)
addFatras(s, geometry, field, rnd, generalMixtureScattering=True)
addDigitization(
    s,
    geometry,
    field,
    rnd=rnd,
    digiConfigFile=a.source / "Examples/Configs/odd-digi-smearing-config.json",
)
addDigiParticleSelection(
    s,
    ParticleSelectorConfig(
        pt=(1 * u.GeV, None), eta=(-3, 3), measurements=(9, None), removeNeutral=True
    ),
)
addSeeding(
    s,
    geometry,
    field,
    initialSigmas=[1 * u.mm, 1 * u.mm, 1 * u.degree, 1 * u.degree, 0, 1 * u.ns],
    initialSigmaQoverPt=0.1 * u.e / u.GeV,
    initialSigmaPtRel=0.1,
    initialVarInflation=[1.0] * 6,
    particleHypothesis=acts.ParticleHypothesis.muon,
    geoSelectionConfigFile=a.source / "Examples/Configs/odd-seeding-config.json",
)

track_selection = acts.TrackSelector.Config(
    ptMin=1 * u.GeV,
    absEtaMax=3.0,
    loc0Min=-4 * u.mm,
    loc0Max=4 * u.mm,
    minMeasurements=7,
    maxHoles=2,
    maxOutliers=2,
)
finder = ex.TrackFindingAlgorithm.makeTrackFinderFunction(geometry, field, level)
collections = []
for name in a.variants:
    tail = not name.startswith("core")
    score = name != "unscored"
    cuts = {
        "core15": (15.0, 25.0),
        "core25": (25.0, 50.0),
        "core49": (49.0, 100.0),
    }.get(name, (15.0, 25.0))
    limit = float(name[4:]) if name.startswith("tail") and name[4:] else float("inf")
    selector = acts.MeasurementSelectorCuts()
    selector.chi2CutOffMeasurement = [cuts[0]]
    selector.chi2CutOffOutlier = [cuts[1]]
    selector.numMeasurementsCutOff = [2]
    selector.chi2CutPerDimension = True
    extra = {}
    if name == "custom":
        # Exercise the public user model with a deliberately different prior.
        extra["scatteringTailModel"] = (
            lambda slab, hyp, qop: ex.ScatteringTailComponent(0.03, 5.0)
        )
    s.addAlgorithm(
        ex.TrackFindingAlgorithm(
            level=level,
            inputMeasurements="measurement_subset",
            inputInitialTrackParameters="estimatedparameters",
            inputSeeds="estimatedseeds",
            outputTracks=name + "_ckf",
            trackingGeometry=geometry,
            magneticField=field,
            findTracks=finder,
            trackSelectorCfg=track_selection,
            measurementSelectorCfg=acts.MeasurementSelector.Config(
                [(acts.GeometryIdentifier(), selector)]
            ),
            seedDeduplication=True,
            stayOnSeed=True,
            twoWay=True,
            pixelVolumeIds=[16, 17, 18],
            stripVolumeIds=[23, 24, 25],
            maxPixelHoles=1,
            maxStripHoles=2,
            constrainToVolumeIds=[
                2,
                32,
                4,
                16,
                17,
                18,
                20,
                23,
                24,
                25,
                26,
                8,
                28,
                29,
                30,
            ],
            scatteringTail=tail,
            scatteringTailScoring=score,
            maxScatteringTailScore=limit,
            **extra,
        )
    )
    s.addAlgorithm(
        ex.GreedyAmbiguityResolutionAlgorithm(
            level=level,
            inputTracks=name + "_ckf",
            outputTracks=name + "_ambi",
            maximumSharedHits=3,
            maximumIterations=1000000,
            nMeasurementsMin=7,
        )
    )
    for stage in ["ckf", "ambi"]:
        key = name + "_" + stage
        collections.append((key, score))
        s.addAlgorithm(
            ex.TrackTruthMatcher(
                level=level,
                inputTracks=key,
                inputParticles="particles",
                inputMeasurementParticlesMap="measurement_particles_map",
                outputTrackParticleMatching=key + "_tp",
                outputParticleTrackMatching=key + "_pt",
                doubleMatching=True,
            )
        )
        s.addWriter(
            RootTrackSummaryWriter(
                level=level,
                inputTracks=key,
                inputParticles="particles_selected",
                inputTrackParticleMatching=key + "_tp",
                filePath=str(a.output / (key + "_tracks.root")),
                treeName="tracksummary",
                writeCovMat=False,
            )
        )
        s.addWriter(
            RootPatternRecognitionPerformanceWriter(
                level=level,
                inputTracks=key,
                inputParticles="particles_selected",
                inputTrackParticleMatching=key + "_tp",
                inputParticleTrackMatching=key + "_pt",
                inputParticleMeasurementsMap="particle_measurements_map",
                filePath=str(a.output / (key + "_performance.root")),
                writeMatchingDetails=True,
            )
        )

modules = Counter()


def count_module(surface):
    g = surface.geometryId
    modules[f"{g.volume}:{g.layer}"] += 1


geometry.visitSurfaces(count_module)


class Diagnostics(ex.IAlgorithm):
    def __init__(self):
        super().__init__(name="TailScoreDiagnostics", level=level)
        self.measurements = ex.ReadDataHandle(
            self, ex.MeasurementContainer, "Measurements"
        )
        self.measurements.initialize("measurements")
        self.inputs = []
        for key, score in collections:
            h = ex.ReadDataHandle(self, ex.ConstTrackContainer, key)
            h.initialize(key)
            self.inputs.append((key, score, h))
        self.out = (a.output / "diagnostics.jsonl").open("w")

    def execute(self, ctx):
        measurements = self.measurements(ctx.eventStore)
        occupancy = Counter()
        digest = hashlib.sha256()
        for measurement in measurements:
            g = measurement.geometryId
            occupancy[f"{g.volume}:{g.layer}"] += 1
            digest.update(int(g.value).to_bytes(8, "little"))
            digest.update(struct.pack("6d", *measurement.fullParameters))
        data = {
            "event": ctx.eventNumber,
            "measurements": len(measurements),
            "occupancy": dict(occupancy),
            "measurement_hash": digest.hexdigest(),
            "tracks": {},
        }
        for key, score, handle in self.inputs:
            tracks = handle(ctx.eventStore)
            rows = []
            for track in tracks:
                if score:
                    value = ex.scatteringTailScore(track)
                    rows.append(
                        [
                            track.index,
                            value.score,
                            value.logLikelihood,
                            value.tailWeight,
                            track.nMeasurements,
                        ]
                    )
                else:
                    rows.append([track.index, None, None, None, track.nMeasurements])
            data["tracks"][key] = rows
        self.out.write(json.dumps(data, allow_nan=False) + "\n")
        self.out.flush()
        print(
            f"EVENT {ctx.eventNumber}: {len(measurements)} measurements; "
            + ", ".join(f"{k}={len(v)}" for k, v in data["tracks"].items()),
            flush=True,
        )
        return ex.ProcessCode.SUCCESS

    def finalize(self):
        self.out.close()
        return ex.ProcessCode.SUCCESS


s.addAlgorithm(Diagnostics())
(a.output / "config.json").write_text(
    json.dumps(
        {
            **vars(a),
            "source": str(a.source),
            "output": str(a.output),
            "modules": dict(modules),
            "simulation": "Fatras GeneralMixture",
            "seed": 42,
            "threads": 1,
        },
        indent=2,
    )
    + "\n"
)
s.run()
