import pathlib

import sys

sys.path = [
    "/home/andreas/cern/source/acts/acts/git1/Examples/Scripts/Python/",
    # "/home/andreas/cern/source/acts/acts/git2/Examples/Scripts/Python/",
] + sys.path

import acts
import acts.examples
from acts.examples.simulation import (
    addParticleGun,
    EtaConfig,
    ParticleConfig,
    addFatras,
    addDigitization,
)
from acts.examples.reconstruction import (
    addSeeding,
    SeedingAlgorithm,
    TruthSeedRanges,
    addKalmanTracks,
)

from acts.examples.odd import getOpenDataDetector

from common import getOpenDataDetectorDirectory

from truth_tracking_kalman import runTruthTrackingKalman


u = acts.UnitConstants
geoDir = getOpenDataDetectorDirectory()
rootOutputDir = pathlib.Path.cwd() / "root_files"

matDeco = acts.IMaterialDecorator.fromFile(
    geoDir / "data/odd-material-maps.root",
    level=acts.logging.INFO,
)
detector, trackingGeometry, decorators = getOpenDataDetector(geoDir, matDeco)
digiConfig = geoDir / "config/odd-digi-smearing-config.json"
geoSel = geoDir / "config/odd-seeding-config.json"

field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))

s = acts.examples.Sequencer(events=10000, numThreads=-1, logLevel=acts.logging.INFO)

rnd = acts.examples.RandomNumbers(seed=42)

addParticleGun(
    s,
    EtaConfig(-2.0, 2.0),
    ParticleConfig(2, acts.PdgParticle.eMuon, False),
    multiplicity=1,
    rnd=rnd,
    outputDirRoot=rootOutputDir,
)

addFatras(
    s,
    trackingGeometry,
    field,
    rnd=rnd,
    outputDirRoot=rootOutputDir,
)

addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=digiConfig,
    rnd=rnd,
    outputDirRoot=rootOutputDir,
)

addSeeding(
    s,
    trackingGeometry,
    field,
    seedingAlgorithm=SeedingAlgorithm.TruthSmeared,
    rnd=rnd,
    truthSeedRanges=TruthSeedRanges(
        pt=(500 * u.MeV, None),
        nHits=(9, None),
    ),
    outputDirRoot=rootOutputDir,
)

addKalmanTracks(
    s,
    trackingGeometry,
    field,
    False,
    0,
)

# Output
s.addWriter(
    acts.examples.RootTrajectoryStatesWriter(
        level=acts.logging.INFO,
        inputTrajectories="trajectories",
        inputParticles="truth_seeds_selected",
        inputSimHits="simhits",
        inputMeasurementParticlesMap="measurement_particles_map",
        inputMeasurementSimHitsMap="measurement_simhits_map",
        filePath=str(rootOutputDir / "trackstates_fitter.root"),
    )
)

s.addWriter(
    acts.examples.RootTrajectorySummaryWriter(
        level=acts.logging.INFO,
        inputTrajectories="trajectories",
        inputParticles="truth_seeds_selected",
        inputMeasurementParticlesMap="measurement_particles_map",
        filePath=str(rootOutputDir / "tracksummary_fitter.root"),
    )
)

s.addWriter(
    acts.examples.TrackFinderPerformanceWriter(
        level=acts.logging.INFO,
        inputProtoTracks="truth_particle_tracks",  # "truth_particle_tracks", "prototracks"
        inputParticles="truth_seeds_selected",
        inputMeasurementParticlesMap="measurement_particles_map",
        filePath=str(rootOutputDir / "performance_track_finder.root"),
    )
)

s.addWriter(
    acts.examples.TrackFitterPerformanceWriter(
        level=acts.logging.INFO,
        inputTrajectories="trajectories",
        inputParticles="truth_seeds_selected",
        inputMeasurementParticlesMap="measurement_particles_map",
        filePath=str(rootOutputDir / "performance_track_fitter.root"),
    )
)

s.addWriter(
    acts.examples.RootTrackParameterWriter(
        level=acts.logging.INFO,
        inputTrackParameters="estimatedparameters",
        inputProtoTracks="truth_particle_tracks",  # "truth_particle_tracks", "prototracks"
        inputParticles="truth_seeds_selected",
        inputSimHits="simhits",
        inputMeasurementParticlesMap="measurement_particles_map",
        inputMeasurementSimHitsMap="measurement_simhits_map",
        filePath=str(rootOutputDir / "estimatedparams.root"),
        treeName="estimatedparams",
    )
)

s.addWriter(
    acts.examples.RootParticleWriter(
        level=acts.logging.INFO,
        inputParticles="truth_seeds_selected",
        filePath=str(rootOutputDir / "truth_seeds_selected.root"),
    )
)

s.run()
