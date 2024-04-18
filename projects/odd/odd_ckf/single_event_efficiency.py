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

oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

detector, trackingGeometry, decorators = getOpenDataDetector(
    geoDir, mdecorator=oddMaterialDeco
)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))

multiplicity = 10
particles = 1

data = {
    "truth": {"vertices": []},
    "smeared": {"track_params": []},
    "ckf": {"track_params": []},
}


def smeared(rnd, outputDir):
    s = acts.examples.Sequencer(
        events=1, skip=1, numThreads=-1, outputDir=str(outputDir)
    )

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
        outputDirRoot=outputDir,
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

    addSeeding(
        s,
        trackingGeometry,
        field,
        # ParticleSmearingSigmas(d0=20*u.um, d0PtA=0, d0PtB=0, z0=20*u.um, z0PtA=0, z0PtB=0),
        seedingAlgorithm=SeedingAlgorithm.TruthSmeared,
        geoSelectionConfigFile=oddSeedingSel,
        outputDirRoot=outputDir,
    )

    addKalmanTracks(
        s,
        trackingGeometry,
        field,
        outputDirRoot=outputDir,
    )

    s.addWriter(
        acts.examples.CsvTrackParameterWriter(
            inputTrajectories="trajectories",
            outputDir=str(outputDir),
            outputStem="trajectory-kf.csv",
            level=acts.logging.Level.VERBOSE,
        )
    )

    s.run()

    particles_data = uproot.open(outputDir / "particles.root")
    particles_data = particles_data["particles"].arrays(
        ["vx", "vy", "vz", "px", "py", "pz"], library="pd"
    )
    for i, (x, y, z, px, py, pz) in particles_data.iterrows():
        data["truth"]["vertices"].append((x, y, z, px, py, pz))

    tracks_data = uproot.open(outputDir / "tracksummary_kf.root")
    tracks_data = tracks_data["tracksummary"].arrays(
        ["eLOC0_fit", "eLOC1_fit", "ePHI_fit", "eTHETA_fit", "eQOP_fit"], library="pd"
    )
    for i, (d0, z0, phi, theta, qop) in tracks_data.iterrows():
        data["smeared"]["track_params"].append((d0, z0, phi, theta, qop))


def ckf(rnd, outputDir):
    s = acts.examples.Sequencer(
        events=1, skip=1, numThreads=-1, outputDir=str(outputDir)
    )

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
        outputDirRoot=outputDir,
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

    s.addWriter(
        acts.examples.CsvTrackParameterWriter(
            inputTrajectories="trajectories",
            outputDir=str(outputDir),
            outputStem="trajectory-ambi.csv",
            level=acts.logging.Level.VERBOSE,
        )
    )

    s.run()

    tracks_data = uproot.open(outputDir / "tracksummary_ambi.root")
    tracks_data = tracks_data["tracksummary"].arrays(
        ["eLOC0_fit", "eLOC1_fit", "ePHI_fit", "eTHETA_fit", "eQOP_fit"], library="pd"
    )
    for _, (d0, z0, phi, theta, qop) in tracks_data.iterrows():
        data["ckf"]["track_params"].append((d0, z0, phi, theta, qop))


outputDir = pathlib.Path.cwd() / "output"
for sim in [smeared, ckf]:
    rnd = acts.examples.RandomNumbers(seed=42)
    sim(rnd, outputDir)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec


def localTracksToGlobal(tracks):
    n = len(tracks)

    p = np.abs(1 / tracks[:, 4])
    pz = p * np.cos(tracks[:, 3])
    pt = p * np.sin(tracks[:, 3])
    px = pt * np.cos(tracks[:, 2])
    py = pt * np.sin(tracks[:, 2])
    pv = np.hstack([px[:, np.newaxis], py[:, np.newaxis], pz[:, np.newaxis]])

    zstack = np.zeros((n, 3))
    zstack[:, 2] = 1

    radiusAxisGlobal = np.cross(zstack, pv)
    radiusAxisGlobal = (
        radiusAxisGlobal / np.linalg.norm(radiusAxisGlobal, axis=-1)[:, np.newaxis]
    )
    return (
        zstack * tracks[:, 1, np.newaxis] + radiusAxisGlobal * tracks[:, 0, np.newaxis],
        pv,
    )


fig = plt.figure()
gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])

ax0 = plt.subplot(gs[0])
ax0.set_xlabel("z")
ax0.set_ylabel("x")

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.set_xlabel("z")
ax1.set_ylabel("y")

vertices = np.array(data["truth"]["vertices"])
p = vertices[:, 3:6] / np.linalg.norm(vertices[:, 3:6], axis=-1)[:, np.newaxis]
ax0.quiver(
    vertices[:, 2], vertices[:, 0], p[:, 2], p[:, 0], angles="uv", units="inches"
)
ax1.quiver(
    vertices[:, 2], vertices[:, 1], p[:, 2], p[:, 1], angles="uv", units="inches"
)
ax0.scatter(vertices[:, 2], vertices[:, 0], label="true")
ax1.scatter(vertices[:, 2], vertices[:, 1], label="true")

tracks = np.array(data["smeared"]["track_params"])
cpoa, p = localTracksToGlobal(tracks)
p = p / np.linalg.norm(p, axis=-1)[:, np.newaxis]
ax0.quiver(cpoa[:, 2], cpoa[:, 0], p[:, 2], p[:, 0], angles="uv", units="inches")
ax1.quiver(cpoa[:, 2], cpoa[:, 1], p[:, 2], p[:, 1], angles="uv", units="inches")
ax0.scatter(cpoa[:, 2], cpoa[:, 0], label="true_smeared_kf")
ax1.scatter(cpoa[:, 2], cpoa[:, 1], label="true_smeared_kf")

tracks = np.array(data["ckf"]["track_params"])
cpoa, p = localTracksToGlobal(tracks)
p = p / np.linalg.norm(p, axis=-1)[:, np.newaxis]
ax0.quiver(cpoa[:, 2], cpoa[:, 0], p[:, 2], p[:, 0], angles="uv", units="inches")
ax1.quiver(cpoa[:, 2], cpoa[:, 1], p[:, 2], p[:, 1], angles="uv", units="inches")
ax0.scatter(cpoa[:, 2], cpoa[:, 0], label="ckf")
ax1.scatter(cpoa[:, 2], cpoa[:, 1], label="ckf")

plt.legend()
plt.show()
