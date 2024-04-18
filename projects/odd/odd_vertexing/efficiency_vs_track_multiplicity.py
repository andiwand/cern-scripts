#!/usr/bin/env python3
import pathlib, acts, acts.examples
from acts.examples.simulation import (
    addParticleGun,
    MomentumConfig,
    EtaConfig,
    ParticleConfig,
    addPythia8,
    addFatras,
    ParticleSelectorConfig,
    addDigitization,
)
from acts.examples.reconstruction import (
    addSeeding,
    SeedingAlgorithm,
    TruthSeedRanges,
    addKalmanTracks,
    addCKFTracks,
    CKFPerformanceConfig,
    TrackSelectorRanges,
    addAmbiguityResolution,
    AmbiguityResolutionConfig,
    addVertexFitting,
    VertexFinder,
)
from common import getOpenDataDetectorDirectory
from acts.examples.odd import getOpenDataDetector

import uproot

u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
outputDir = pathlib.Path.cwd() / "output"

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(
    geoDir, mdecorator=oddMaterialDeco
)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))

data = {
    VertexFinder.Iterative: {
        "particles": [],
        "mean": [],
        "std": [],
    },
    VertexFinder.AMVF: {
        "particles": [],
        "mean": [],
        "std": [],
    },
}

multiplicity = 10

for vertexing in [VertexFinder.Iterative, VertexFinder.AMVF]:
    for particles in range(2, 11):
        rnd = acts.examples.RandomNumbers(seed=42)

        s = acts.examples.Sequencer(events=100, numThreads=-1, outputDir=str(outputDir))

        addParticleGun(
            s,
            MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, transverse=True),
            EtaConfig(-3.0, 3.0, uniform=True),
            ParticleConfig(particles, acts.PdgParticle.eMuon, randomizeCharge=True),
            vtxGen=acts.examples.GaussianVertexGenerator(
                stddev=acts.Vector4(12.5 * u.um, 12.5 * u.um, 55.5 * u.mm, 0.0 * u.ns),
                mean=acts.Vector4(0, 0, 0, 0),
            ),
            multiplicity=multiplicity,
            rnd=rnd,
        )

        addFatras(
            s,
            trackingGeometry,
            field,
            rnd=rnd,
            outputDirRoot=outputDir,
        )

        addDigitization(
            s,
            trackingGeometry,
            field,
            digiConfigFile=oddDigiConfig,
            rnd=rnd,
            outputDirRoot=outputDir,
        )

        """
    addSeeding(
        s,
        trackingGeometry,
        field,
        #ParticleSmearingSigmas(d0=20*u.um, d0PtA=0, d0PtB=0, z0=20*u.um, z0PtA=0, z0PtB=0),
        seedingAlgorithm=SeedingAlgorithm.TruthSmeared,
        geoSelectionConfigFile=oddSeedingSel,
        outputDirRoot=outputDir,
    )

    addKalmanTracks(
        s,
        trackingGeometry,
        field,
    )
    """

        addSeeding(
            s,
            trackingGeometry,
            field,
            geoSelectionConfigFile=oddSeedingSel,
            outputDirRoot=outputDir,
        )

        addCKFTracks(
            s,
            trackingGeometry,
            field,
            CKFPerformanceConfig(ptMin=0.0, nMeasurementsMin=6),
            TrackSelectorRanges(
                pt=(1.0 * u.GeV, None), absEta=(None, 3.0), removeNeutral=True
            ),
            outputDirRoot=outputDir,
        )

        addAmbiguityResolution(
            s,
            AmbiguityResolutionConfig(maximumSharedHits=3),
            CKFPerformanceConfig(ptMin=0.0, nMeasurementsMin=6),
            outputDirRoot=outputDir,
        )

        addVertexFitting(
            s,
            field,
            TrackSelectorRanges(
                pt=(0.5 * u.GeV, None),
                loc0=(-4.0 * u.mm, 4.0 * u.mm),
                absEta=(None, 3.0),
                removeNeutral=True,
            ),
            vertexFinder=vertexing,
            outputDirRoot=outputDir,
            logLevel=acts.logging.Level.VERBOSE,
        )

        s.run()

        vertex_perf = uproot.open(outputDir / "performance_vertexing.root")
        vertex_perf = vertex_perf["vertexing"].arrays(library="pd")
        data[vertexing]["particles"].append(particles)
        data[vertexing]["mean"].append(vertex_perf["nRecoVtx"].mean())
        data[vertexing]["std"].append(vertex_perf["nRecoVtx"].std())

import numpy as np
import matplotlib.pyplot as plt

vertexing_label = {
    VertexFinder.Iterative: "IVF",
    VertexFinder.AMVF: "AMVF",
}

plt.axhline(y=multiplicity, color="black", label="true")
for vertexing in [VertexFinder.Iterative, VertexFinder.AMVF]:
    plt.errorbar(
        data[vertexing]["particles"],
        data[vertexing]["mean"],
        yerr=data[vertexing]["std"],
        fmt="o",
        capsize=3,
        capthick=3,
        alpha=0.7,
        label=vertexing_label[vertexing],
    )
plt.xlabel("tracks per vertex")
plt.ylabel("reconstructed vertices")
plt.legend()
plt.show()
