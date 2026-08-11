#!/usr/bin/env python3
"""Seed track parameter resolution for single muons in the ODD.

Simulates single muons at a fixed pT with flat eta, finds them with either
truth seeding or triplet seeding, and writes the residual/pull performance of
the seed-estimated track parameters at the perigee, one ROOT file per variant.

The variants differ in which space points the estimate is built from:

  truth_all      truth seed with every pixel space point on the track,
                 least-squares helix fit
  truth_inner3   truth seed with the three innermost space points
  truth_spread3  truth seed with the innermost, the middle and the outermost
                 space point
  triplet        grid triplet seeding, default three-point estimate

All variants are extrapolated to a perigee at the origin before the comparison
with truth, so the numbers are on the same footing.

Every point runs twice: a short calibration pass on wide axes measures the
residual widths, then the production pass puts regular axes around them. The
widths span more than an order of magnitude between the variants, and the
Gaussian core fit the performance writer runs on the way out needs the core
resolved and the axis untruncated at the same time.
"""

from pathlib import Path

import numpy as np

import acts
import acts.examples
import acts.examples.root
from acts.examples.simulation import (
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    ParticleSelectorConfig,
    addParticleGun,
    addFatras,
    addDigitization,
    addDigiParticleSelection,
)
from acts.examples.reconstruction import (
    SeedingAlgorithm,
    TruthEstimatedSeedingAlgorithmConfigArg,
    addSeeding,
    addTrackParameterPerformanceWriter,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

import argparse

u = acts.UnitConstants

# name -> (seeding algorithm, truth space point selection, fit all space points)
VARIANTS = {
    "truth_all": (
        SeedingAlgorithm.TruthEstimated,
        acts.examples.TruthSeedSpacePointSelection.All,
        True,
    ),
    "truth_inner3": (
        SeedingAlgorithm.TruthEstimated,
        acts.examples.TruthSeedSpacePointSelection.InnermostTriplet,
        False,
    ),
    "truth_spread3": (
        SeedingAlgorithm.TruthEstimated,
        acts.examples.TruthSeedSpacePointSelection.SpreadTriplet,
        False,
    ),
    "triplet": (SeedingAlgorithm.GridTriplet, None, False),
}

# Half range of the residual axes for the calibration pass. It only has to be
# generous, since the production pass sizes its axes on what that pass measures.
# Momentum-dependent axes carry a `perPt` factor of 1/pT[GeV].
RESIDUAL_AXES = {
    "d0": dict(half=100 * u.mm, label="r_{d0} [mm]"),
    "z0": dict(half=200 * u.mm, label="r_{z0} [mm]"),
    "phi": dict(half=1.0, label="r_{#phi} [rad]"),
    "theta": dict(half=1.0, label="r_{#theta} [rad]"),
    "qop": dict(half=20.0, perPt=True, label="r_{q/p} [c/GeV]"),
    "qopt": dict(half=20.0, perPt=True, label="r_{q/pT} [c/GeV]"),
    "qopt_rel": dict(half=20.0, label="r_{rel q/pT}"),
    "t": dict(half=100.0, label="r_{t} [mm/c]"),
}

# Width at zero of the calibration axes, as a fraction of their half range.
CALIBRATION_FINEST = 5e-5


def asinhAxis(bins, half, finest, title):
    """Symmetric axis with `sinh` spaced edges, fine at zero, coarse in the tails.

    Reaches far into the tails without losing the core, which is what an
    unknown residual scale needs. `finest` is the width of the bin at zero as a
    fraction of `half`.
    """
    import math

    # edge(t) = half * sinh(k t) / sinh(k) for t in [-1, 1]; solve for the k
    # that gives the requested width at zero
    target = finest * bins / 2
    lo, hi = 1e-6, 50.0
    for _ in range(200):
        k = 0.5 * (lo + hi)
        if k / math.sinh(k) > target:
            lo = k
        else:
            hi = k
    k = 0.5 * (lo + hi)

    edges = [
        half * math.sinh(k * (2 * i / bins - 1)) / math.sinh(k)
        for i in range(bins + 1)
    ]
    return acts.Axis.variable(edges, title)


def resPlotToolConfig(pt, args, halfRanges=None):
    """Residual and pull binning.

    Without `halfRanges` the residual axes are the wide asinh ones of the
    calibration pass. With them they are regular, because the Gaussian core fit
    the writer runs on the way out fits bin contents rather than a density and
    would read a variable bin width as extra population in the tails.
    """
    ptGeV = pt / u.GeV

    cfg = acts.examples.root.ResPlotToolConfig()
    binning = {
        "Eta": acts.Axis.regular(args.etaBins, args.eta[0], args.eta[1], "#eta"),
        "Phi": acts.Axis.regular(40, -3.15, 3.15, "#phi [rad]"),
        "Pt": acts.Axis.regular(40, 0, 2 * ptGeV, "pT [GeV/c]"),
        "Pull": acts.Axis.regular(100, -5, 5, "pull"),
    }
    for name, spec in RESIDUAL_AXES.items():
        key = f"Residual_{name}"
        if halfRanges is None:
            half = spec["half"]
            if spec.get("perPt"):
                half /= ptGeV
            binning[key] = asinhAxis(
                args.calibrationBins, half, CALIBRATION_FINEST, spec["label"]
            )
        else:
            half = halfRanges[name] * args.residualScale
            binning[key] = acts.Axis.regular(
                args.residualBins, -half, half, spec["label"]
            )
    cfg.varBinning = binning
    return cfg


def measureHalfRanges(path, pt, args):
    """Half ranges for the production axes, from a calibration file.

    The width varies by an order of magnitude across eta, and one axis has to
    serve all of it: sized on the widest eta bins the central ones lose their
    core to a coarse binning, sized on the central ones the forward cores fall
    off the axis. A high percentile splits the difference.
    """
    import uproot

    halfRanges = {}
    with uproot.open(path) as handle:
        for name, spec in RESIDUAL_AXES.items():
            hist = handle[f"res_{name}_vs_eta"]
            edges = hist.axis(1).edges()
            widths = []
            for row in hist.values():
                n = row.sum()
                if n < args.calibrationMinEntries:
                    continue
                cumulative = np.concatenate([[0.0], np.cumsum(row)]) / n
                lo, hi = np.interp([0.158655, 0.841345], cumulative, edges)
                widths.append(0.5 * (hi - lo))
            if widths:
                scale = np.percentile(widths, args.calibrationPercentile)
            else:
                scale = 0.0
            if scale > 0:
                halfRanges[name] = args.residualRangeSigmas * scale
            else:
                # nothing to measure, e.g. the time residual of a seed
                fallback = spec["half"]
                if spec.get("perPt"):
                    fallback /= pt / u.GeV
                halfRanges[name] = fallback
    return halfRanges


def run(args, detector, field, variant, pt, outputDir, events, halfRanges, label):
    trackingGeometry = detector.trackingGeometry()
    geoDir = getOpenDataDetectorDirectory()
    seedingAlgorithm, spacePointSelection, estimateFromAllSpacePoints = VARIANTS[
        variant
    ]

    rnd = acts.examples.RandomNumbers(seed=args.seed)
    s = acts.examples.Sequencer(
        events=events,
        numThreads=args.threads,
        logLevel=acts.logging.INFO,
    )

    addParticleGun(
        s,
        momentumConfig=MomentumConfig(pt, pt, transverse=True),
        etaConfig=EtaConfig(args.eta[0], args.eta[1], uniform=True),
        phiConfig=PhiConfig(0.0, 360.0 * u.degree),
        particleConfig=ParticleConfig(
            1, acts.PdgParticle.eMuon, randomizeCharge=True
        ),
        rnd=rnd,
    )

    addFatras(
        s,
        trackingGeometry,
        field,
        enableInteractions=True,
        rnd=rnd,
    )

    addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=geoDir / "config/odd-digi-smearing-config.json",
        rnd=rnd,
    )

    # the same particle selection for every variant, so they are compared on
    # the same set of muons
    addDigiParticleSelection(
        s,
        ParticleSelectorConfig(
            pt=(0.5 * pt, None),
            eta=args.eta,
            measurements=(args.minMeasurements, None),
            removeNeutral=True,
        ),
    )

    addSeeding(
        s,
        trackingGeometry,
        field,
        seedingAlgorithm=seedingAlgorithm,
        truthEstimatedSeedingAlgorithmConfigArg=TruthEstimatedSeedingAlgorithmConfigArg(
            spacePointSelection=spacePointSelection,
        ),
        estimateFromAllSpacePoints=estimateFromAllSpacePoints,
        geometricRefineIterations=args.refineIterations,
        geoSelectionConfigFile=geoDir / "config/odd-seeding-config.json",
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
    )

    addTrackParameterPerformanceWriter(
        s,
        outputDir,
        tracks="seed-tracks",
        particles="particles_selected",
        trackingGeometry=trackingGeometry,
        field=field,
        resPlotToolConfig=resPlotToolConfig(pt, args, halfRanges),
        outputName=label,
    )

    s.run()
    return outputDir / f"performance_{label}.root"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputDir", help="Output directory", type=Path)
    parser.add_argument(
        "--events", help="Number of muons per point", type=int, default=10000
    )
    parser.add_argument("--threads", help="Number of threads", type=int, default=-1)
    parser.add_argument("--seed", help="Random seed", type=int, default=42)
    parser.add_argument(
        "--pt",
        help="Transverse momenta in GeV",
        type=float,
        nargs="+",
        default=[1.0, 10.0, 100.0],
    )
    parser.add_argument(
        "--variants",
        help="Variants to run",
        nargs="+",
        choices=list(VARIANTS),
        default=list(VARIANTS),
    )
    parser.add_argument(
        "--eta", help="Eta range", type=float, nargs=2, default=[-3.0, 3.0]
    )
    parser.add_argument("--eta-bins", dest="etaBins", type=int, default=24)
    parser.add_argument("--residual-bins", dest="residualBins", type=int, default=200)
    parser.add_argument(
        "--residual-scale",
        dest="residualScale",
        help="Widen or narrow all residual axes on top of the calibration",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--residual-range-sigmas",
        dest="residualRangeSigmas",
        help="Half range of the residual axes in units of the calibrated width",
        type=float,
        default=6.0,
    )
    parser.add_argument(
        "--calibration-percentile",
        dest="calibrationPercentile",
        help="Percentile over the eta bins that sets the residual axis scale",
        type=float,
        default=90.0,
    )
    parser.add_argument(
        "--calibration-events",
        dest="calibrationEvents",
        help="Muons in the pass that sizes the residual axes, 0 to reuse the wide axes",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--calibration-bins", dest="calibrationBins", type=int, default=400
    )
    parser.add_argument(
        "--calibration-min-entries",
        dest="calibrationMinEntries",
        help="Entries an eta bin needs before it sizes the axes",
        type=int,
        default=50,
    )
    parser.add_argument(
        "--min-measurements",
        dest="minMeasurements",
        help="Measurements required of a muon to enter the study",
        type=int,
        default=9,
    )
    parser.add_argument(
        "--refine-iterations",
        dest="refineIterations",
        help="Geometric refinement iterations of the multi-point helix fit",
        type=int,
        default=0,
    )
    args = parser.parse_args()

    args.outputDir = args.outputDir.resolve()
    args.outputDir.mkdir(parents=True, exist_ok=True)

    geoDir = getOpenDataDetectorDirectory()
    materialDeco = acts.IMaterialDecorator.fromFile(
        geoDir / "data/odd-material-maps.root"
    )
    detector = getOpenDataDetector(odd_dir=geoDir, materialDecorator=materialDeco)
    field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))

    calibrationDir = args.outputDir / "calibration"
    if args.calibrationEvents > 0:
        calibrationDir.mkdir(exist_ok=True)

    for ptGeV in args.pt:
        pt = ptGeV * u.GeV
        for variant in args.variants:
            label = f"{variant}_pt{round(ptGeV)}"

            halfRanges = None
            if args.calibrationEvents > 0:
                print(f"=== {label} (calibration) ===", flush=True)
                path = run(
                    args,
                    detector,
                    field,
                    variant,
                    pt,
                    calibrationDir,
                    args.calibrationEvents,
                    None,
                    label,
                )
                halfRanges = measureHalfRanges(path, pt, args)

            print(f"=== {label} ===", flush=True)
            run(
                args,
                detector,
                field,
                variant,
                pt,
                args.outputDir,
                args.events,
                halfRanges,
                label,
            )


if __name__ == "__main__":
    main()
