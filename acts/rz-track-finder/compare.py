#!/usr/bin/env python3
"""Run the CKF or the RZ finder on the same simulated events and write the
usual performance files, so that the two can be compared file against file.

    compare.py --finder ckf --out out/ckf
    compare.py --finder rz  --out out/rz
"""

import argparse
from pathlib import Path

import acts
from acts import UnitConstants as u
from acts.examples import GenericDetector
from acts.examples.simulation import (
    addParticleGun,
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    addFatras,
    addDigitization,
    ParticleSelectorConfig,
    addDigiParticleSelection,
    addPythia8,
)
from acts.examples.reconstruction import (
    addSeeding,
    SeedFinderConfigArg,
    SeedFinderOptionsArg,
    SeedingAlgorithm,
    addCKFTracks,
    addTrackWriters,
    TrackSelectorConfig,
    CkfConfig,
)

srcdir = Path(__file__).resolve().parents[0]
actsdir = Path.home() / "cern/source/acts/acts/dev3"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--finder", choices=["ckf", "rz"], required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--events", type=int, default=100)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--ttbar", action="store_true", help="pythia ttbar instead of muons")
    p.add_argument("--pileup", type=int, default=0)
    p.add_argument("--chi2", type=float, default=15.0)
    p.add_argument("--two-way", action="store_true", help="CKF second pass")
    p.add_argument("--log", default="INFO")
    p.add_argument("--no-material", action="store_true")
    p.add_argument("--odd", action="store_true", help="OpenDataDetector instead of the generic detector")
    p.add_argument("--itk", action="store_true", help="ITk from ~/cern/source/acts/acts-itk, with its field map")
    p.add_argument("--write-states", action="store_true")
    p.add_argument("--inflation", type=float, default=100.0)
    p.add_argument("--backward-layers", type=int, default=6)
    p.add_argument("--max-holes", type=int, default=3)
    p.add_argument("--max-consecutive-holes", type=int, default=2)
    p.add_argument("--window-sigmas", type=float, default=5.0)
    p.add_argument("--max-per-layer", type=int, default=2)
    p.add_argument("--qop-scale", type=float, default=1.0)
    args = p.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    level = getattr(acts.logging, args.log)

    seedingConfigs = None
    excludeVolumes = []
    if args.itk:
        import importlib

        actsroot = importlib.import_module("acts.root")
        itk = importlib.import_module("acts.examples.itk")
        geo_dir = Path.home() / "cern/source/acts/acts-itk"
        detector = itk.buildITkGeometry(geo_dir, logLevel=acts.logging.WARNING)
        digiConfig = geo_dir / "itk-hgtd/itk-smearing-config-no-hgtd.json"
        geoSel = geo_dir / "itk-hgtd/geoSelection-ITk.json"
        field = actsroot.MagneticFieldMapXyz(str(geo_dir / "bfield/ATLAS-BField-xyz.root"))
        seedingConfigs = itk.itkSeedingAlgConfig(itk.InputSpacePointsType.PixelSpacePoints)
        excludeVolumes = [2, 25]  # HGTD
    elif args.odd:
        from acts.examples.odd import getOpenDataDetector

        detector = getOpenDataDetector()
        digiConfig = actsdir / "Examples/Configs/odd-digi-smearing-config.json"
        geoSel = actsdir / "Examples/Configs/odd-seeding-config.json"
    else:
        detector = GenericDetector()
        digiConfig = actsdir / "Examples/Configs/generic-digi-smearing-config.json"
        geoSel = actsdir / "Examples/Configs/generic-seeding-config.json"
    trackingGeometry = detector.trackingGeometry()
    if not args.itk:
        field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))
    rnd = acts.examples.RandomNumbers(seed=42)

    s = acts.examples.Sequencer(
        events=args.events, numThreads=args.threads, logLevel=level, outputDir=str(out)
    )

    if args.ttbar:
        addPythia8(
            s,
            hardProcess=["Top:qqbar2ttbar=on"],
            npileup=args.pileup,
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5 * u.ns),
            ),
            rnd=rnd,
        )
    else:
        addParticleGun(
            s,
            MomentumConfig(1 * u.GeV, 10 * u.GeV, transverse=True),
            EtaConfig(-2.5, 2.5, uniform=True),
            PhiConfig(0.0, 360.0 * u.degree),
            ParticleConfig(4, acts.PdgParticle.eMuon, randomizeCharge=True),
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 1 * u.ns),
            ),
            multiplicity=2,
            rnd=rnd,
        )

    addFatras(s, trackingGeometry, field, enableInteractions=True, rnd=rnd)
    addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=digiConfig,
        rnd=rnd,
    )
    addDigiParticleSelection(
        s,
        ParticleSelectorConfig(pt=(0.5 * u.GeV, None), measurements=(9, None), removeNeutral=True),
    )
    if seedingConfigs is None:
        seedingConfigs = (
            SeedFinderConfigArg(
                r=(None, 200 * u.mm),
                deltaR=(1 * u.mm, 300 * u.mm),
                collisionRegion=(-250 * u.mm, 250 * u.mm),
                z=(-2000 * u.mm, 2000 * u.mm),
                maxSeedsPerSpM=1,
                sigmaScattering=5,
                radLengthPerSeed=0.1,
                minPt=500 * u.MeV,
                impactMax=3 * u.mm,
            ),
            SeedFinderOptionsArg(bFieldInZ=2 * u.T, beamPos=(0.0, 0.0)),
        )
    addSeeding(
        s,
        trackingGeometry,
        field,
        *seedingConfigs,
        seedingAlgorithm=SeedingAlgorithm.GridTriplet,
        initialSigmas=[1 * u.mm, 1 * u.mm, 1 * u.degree, 1 * u.degree, 0 * u.e / u.GeV, 1 * u.ns],
        initialSigmaQoverPt=0.1 * u.e / u.GeV,
        initialSigmaPtRel=0.1,
        initialVarInflation=[1.0] * 6,
        geoSelectionConfigFile=geoSel,
        outputDirRoot=out,
    )

    selector = TrackSelectorConfig(
        pt=(0.5 * u.GeV, None), loc0=(-4.0 * u.mm, 4.0 * u.mm), nMeasurementsMin=6
    )
    if args.finder == "ckf":
        addCKFTracks(
            s,
            trackingGeometry,
            field,
            selector,
            CkfConfig(
                chi2CutOffMeasurement=args.chi2,
                chi2CutOffOutlier=25.0,
                numMeasurementsCutOff=1,
                seedDeduplication=False,
                stayOnSeed=False,
            ),
            twoWay=args.two_way,
            outputDirRoot=out,
            writeTrackStates=args.write_states,
        )
    else:
        finder = acts.examples.RzTrackFindingAlgorithm(
            level=level,
            inputMeasurements="measurements",
            inputInitialTrackParameters="estimatedparameters",
            outputTracks="rz_tracks",
            trackingGeometry=trackingGeometry,
            magneticField=field,
            excludeVolumes=excludeVolumes,
            chi2Cut=args.chi2,
            minMeasurements=6,
            applyMaterial=not args.no_material,
            backwardInflation=args.inflation,
            backwardLayers=args.backward_layers,
            maxHoles=args.max_holes,
            maxConsecutiveHoles=args.max_consecutive_holes,
            windowSigmas=args.window_sigmas,
            maxMeasurementsPerLayer=args.max_per_layer,
            backwardQOverPScale=args.qop_scale,
        )
        s.addAlgorithm(finder)
        matchAlg = acts.examples.TrackTruthMatcher(
            level=level,
            inputTracks="rz_tracks",
            inputParticles="particles_selected",
            inputMeasurementParticlesMap="measurement_particles_map",
            outputTrackParticleMatching="rz_track_particle_matching",
            outputParticleTrackMatching="rz_particle_track_matching",
            doubleMatching=True,
        )
        s.addAlgorithm(matchAlg)
        s.addWhiteboardAlias("track_particle_matching", "rz_track_particle_matching")
        s.addWhiteboardAlias("particle_track_matching", "rz_particle_track_matching")
        addTrackWriters(
            s,
            name="rz",
            tracks="rz_tracks",
            outputDirRoot=out,
            writeSummary=True,
            writeStates=args.write_states,
            writeFitterPerformance=True,
            writeFinderPerformance=True,
        )

    with detector:
        s.run()


if __name__ == "__main__":
    main()
