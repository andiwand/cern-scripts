#!/usr/bin/env python3
"""Fit `ActsFatras::Synthetic::EventConfig` to a full simulation.

Usage:

    ./fit_event_config.py itk --fullsim <GNN4ITk dump>.root --events 5
    ./fit_event_config.py odd --events 20

Some of the parameters follow from the full-simulation distributions directly -
the primary yield is a count, the two beam-spot widths are widths - so those are
computed rather than fitted. What is left is the secondary yield, which is solved
for so that the space point count comes out right rather than fitted to the
truth-level secondary count.

That choice is the point of the whole exercise, so it is worth spelling out. The
generator's secondaries are not only the real secondaries: they also stand in for
the clusters of everything the primary list does not contain, which in ColliderML
is a third of the pixel clusters and in the ITk dump about half. The truth-level
secondary count therefore cannot be matched and should not be; what a seeder sees
is the space point density, and that is what is fitted here.

Prints the fitted configuration as the C++ of a preset, ready to paste into
`Fatras/src/Synthetic/EventGenerator.cpp`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from acts.fatras import synthetic as syn
from scipy.optimize import minimize

import fastsim  # noqa: F401  (kept importable alongside the loaders)

def robust_sigma(values: np.ndarray) -> float:
    """Width of the core of a distribution, ignoring its tails.

    The interquartile range of a Gaussian is 1.349 sigma. Using it rather than
    the standard deviation matters for both references: their z0 and d0 have
    tails that a single Gaussian cannot describe, and it is the core that the
    generator's one Gaussian should reproduce.

    @param values the sample
    @return the equivalent Gaussian sigma
    """
    lo, hi = np.percentile(values, [25, 75])
    return (hi - lo) / 1.349


def fit_pt_spectrum(pt: np.ndarray, min_pt: float = 0.1):
    """Fit `dN/dpT ~ (1 + pT/S)^-n` to a momentum spectrum.

    Done on the closed-form integral rather than by generating, over log-spaced
    bins so that the tail is represented at all, and weighted by the square root
    of the reference count in each bin.

    That weight is the whole of the compromise, so it is worth saying what the
    alternatives cost. Two parameters cannot follow a real spectrum everywhere.
    Weighting every bin equally fits the tail and leaves the mean momentum 14 %
    low; weighting every track equally fits the mean and leaves a tenth of the
    tracks the reference has above 10 GeV; pinning the fractions above 1 and 5 GeV
    exactly gets both of those and misses at 10 GeV by a factor three. The square
    root sits between the first two and is the only one of the four that improves
    every figure at once over the untuned spectrum -- mean to a percent, the
    fraction above 1 GeV from 32 % out to 11 %, above 10 GeV from a fiftieth of the
    reference to a half of it.

    @param pt the reference spectrum in GeV
    @param min_pt the lower end of the generated spectrum in GeV
    @return (ptScale, ptExponent)
    """
    bins = np.logspace(np.log10(min_pt), np.log10(30.0), 26)
    counts, _ = np.histogram(pt, bins=bins)
    weight = np.sqrt(counts.astype(float))
    data = counts / counts.sum()
    filled = counts > 0

    def above(x, scale, exponent):
        return ((scale + x) / (scale + min_pt)) ** (1.0 - exponent)

    def objective(logs):
        scale, exponent = np.exp(logs)
        # below one the spectrum has no finite integral, and the sampler inverts
        # a power that changes sign there
        if exponent <= 1.01:
            return 1e6
        model = above(bins[:-1], scale, exponent) - above(bins[1:], scale,
                                                          exponent)
        model = np.maximum(model, 1e-12)
        model /= model.sum()
        residual = np.log(model[filled]) - np.log(data[filled])
        return (np.sum(weight[filled] * residual**2) / np.sum(weight[filled]))

    result = minimize(objective, np.log([4.7, 11.0]), method="Nelder-Mead",
                      options={"xatol": 1e-4, "fatol": 1e-10, "maxiter": 3000})
    return tuple(np.exp(result.x))


class Target:
    """What the fast simulation is being fitted to, all per event."""

    def __init__(self, full, extent) -> None:
        primary = full.primary
        self.num_events = full.num_events
        # the population the generator's primary list corresponds to
        self.primaries = primary.sum() / full.num_events
        self.z0_sigma = robust_sigma(full.z0[primary])
        self.d0_sigma = robust_sigma(full.d0[primary])
        self.space_points = len(full.sp_x) / full.num_events

        self.r_bins = extent.r_bins(40)
        self.z_bins = np.linspace(0, extent.z_max, 40)
        r = np.hypot(full.sp_x, full.sp_y)
        self.r_profile = self._profile(r, self.r_bins, full.num_events)
        self.z_profile = self._profile(np.abs(full.sp_z), self.z_bins,
                                       full.num_events)

        # The secondary momentum spectrum is not fitted: an exponential cannot
        # follow the full simulation, whose secondaries reach ten GeV where the
        # generator's run out below two, and putting it in the objective made it
        # the only term that mattered. Its one parameter is the mean instead,
        # which is what an exponential above `secondaryMinPt` has to offer.
        self.secondary_mean_pt = full.pt[~primary].mean()
        self.primary_pt = full.pt[primary]

    @staticmethod
    def _profile(values, bins, num_events) -> np.ndarray:
        h, _ = np.histogram(values, bins=bins)
        return h / num_events


def _fast_profiles(layout, config, target: Target):
    """Generate one event and reduce it the same way the target was reduced."""
    event = syn.generateEvent(layout, config)

    x = np.fromiter((sp.x for sp in event.spacePoints), dtype=np.float32,
                    count=len(event.spacePoints))
    y = np.fromiter((sp.y for sp in event.spacePoints), dtype=np.float32,
                    count=len(event.spacePoints))
    z = np.fromiter((sp.z for sp in event.spacePoints), dtype=np.float32,
                    count=len(event.spacePoints))

    # the same selection the loaders apply, so the pt spectrum compares
    return {
        "space_points": float(len(x)),
        "r_profile": Target._profile(np.hypot(x, y), target.r_bins, 1),
        "z_profile": Target._profile(np.abs(z), target.z_bins, 1),
    }


def _mismatch(fast, target: Target) -> float:
    """Squared log-ratio of the profiles, plus the total count.

    The log is what makes this a shape comparison: a plain difference would be
    dominated by the innermost barrel layer, which holds an order of magnitude
    more space points than an endcap disk bin. Only bins both samples fill enter,
    the layout being fixed - where one of them has no surface at all, no setting
    of these three parameters can help.

    The two profiles are normalised to their own totals first, so that they carry
    shape only; the count is matched by `solve_secondary_rate` rather than traded
    against them here.
    """
    total = 0.0
    for name in ("r_profile", "z_profile"):
        a = np.asarray(getattr(target, name), dtype=float)
        b = np.asarray(fast[name], dtype=float)
        both = (a > 0) & (b > 0)
        if not both.any():
            return 1e6
        a = a[both] / a[both].sum()
        b = b[both] / b[both].sum()
        total += np.mean(np.log(b / a) ** 2)
    return total


def solve_charged_per_unit_eta(layout, config, target: Target) -> float:
    """Find the primary yield that leaves the right number of primaries with hits.

    Not simply the count divided by the pile-up and the eta span: not every
    generated primary leaves a space point, and how many do depends on the
    momentum spectrum, so it has to be counted rather than assumed. The number
    with hits is proportional to the number generated, which makes this one step
    rather than a search.

    @param layout the detector to generate on
    @param config the configuration, whose own yield is the reference point
    @param target what to match
    @return the yield that lands on `target.primaries`
    """
    event = syn.generateEvent(layout, config)
    with_hits = sum(1 for p in event.particles if p.primary and p.numHits > 0)
    if with_hits == 0:
        return config.chargedPerUnitEta
    return config.chargedPerUnitEta * target.primaries / with_hits


def solve_secondary_rate(layout, config, target: Target) -> float:
    """Find the `secondaryRate` that reproduces the space point count.

    The count is linear in the rate: the primary hits do not depend on it at all,
    and only one generation of secondaries is produced, so their Poisson mean -
    and with it their hit count - scales with it. One generation therefore
    determines the answer outright, no iteration needed.

    @param layout the detector to generate on
    @param config the configuration, whose own `secondaryRate` is the reference
           point the extrapolation starts from
    @param target what to match
    @return the rate that lands on `target.space_points`
    """
    summary = syn.summarize(syn.generateEvent(layout, config), 1.0)
    if summary.secondaryHits == 0:
        return config.secondaryRate
    wanted = target.space_points - summary.primaryHits
    return config.secondaryRate * wanted / summary.secondaryHits


def _with(config, values: dict):
    """Copy a configuration with some fields replaced.

    `EventConfig` has no copy constructor exposed, so the fields are carried over
    by hand. Only the ones this script touches are copied, which is why the base
    configuration has to be the one everything else is taken from.
    """
    out = syn.EventConfig()
    for name in ("pileup", "chargedPerUnitEta", "minPt", "ptScale",
                 "ptExponent", "minEta", "maxEta", "beamspotSigmaZ", "d0Sigma",
                 "secondaryRate", "secondaryMinPt", "secondaryPtSlope",
                 "secondaryOpeningAngle",
                 "positionSmearing", "sensorThickness", "bFieldZ", "seed"):
        setattr(out, name, getattr(config, name))
    for name, value in values.items():
        setattr(out, name, float(value))
    return out


def report(config, layout, target: Target) -> None:
    """Print what the fitted configuration produces next to the target."""
    fast = _fast_profiles(layout, config, target)
    print("\n%-24s %12s %12s %8s" % ("", "full sim", "fast sim", "ratio"))
    for label, a, b in (
        ("space points/event", target.space_points, fast["space_points"]),
        ("primaries/event", target.primaries, float(config.numPrimaries())),
    ):
        print("%-24s %12.1f %12.1f %8.2f" % (label, a, b, b / a))
    print("%-24s %12.4f %12.4f %8.2f" % ("z0 sigma [mm]", target.z0_sigma,
                                         config.beamspotSigmaZ,
                                         config.beamspotSigmaZ / target.z0_sigma))
    print("%-24s %12.4f %12.4f %8.2f" % ("d0 sigma [mm]", target.d0_sigma,
                                         config.d0Sigma,
                                         config.d0Sigma / target.d0_sigma))


def as_cpp(config, name: str, provenance: str) -> str:
    """Print the configuration as the body of a preset function."""
    lines = [
        "EventConfig EventConfig::%s() {" % name,
        "  // %s" % provenance,
        "  EventConfig config;",
    ]
    for field, fmt in (("chargedPerUnitEta", "%.2ff"),
                       ("ptScale", "%.3ff"),
                       ("ptExponent", "%.2ff"),
                       # "%.0ff" would print 50 as "50f", which is not a literal
                       ("beamspotSigmaZ", "%.0f.f"),
                       ("d0Sigma", "%.4ff"),
                       ("secondaryRate", "%.3ff"),
                       ("secondaryPtSlope", "%.3ff")):
        lines.append(("  config.%s = " + fmt + ";") % (field,
                                                       getattr(config, field)))
    lines += ["  return config;", "}"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("detector", choices=("itk", "odd"))
    parser.add_argument("--fullsim", default=None,
                        help="the ITk dump; unused for the ODD, which downloads")
    parser.add_argument("--events", type=int, default=None)
    parser.add_argument("--pileup", type=int, default=200)
    args = parser.parse_args()

    import validate  # for the per-detector axis extents

    if args.detector == "itk":
        import fullsim_itk

        full = fullsim_itk.load(args.fullsim, num_events=args.events or 5)
        layout = syn.makeItkPixelLayout()
        extent = validate.ITK_EXTENT
        provenance = "Fitted against five events of a GNN4ITk ttbar pu200 dump."
    else:
        import fullsim_colliderml

        full = fullsim_colliderml.load(num_events=args.events or 20)
        layout = syn.makeOpenDataDetectorPixelLayout()
        extent = validate.ODD_EXTENT
        provenance = ("Fitted against twenty events of ColliderML "
                      "ttbar_pu200.")

    print("full simulation: %d events, %d space points"
          % (full.num_events, len(full.sp_x)))
    target = Target(full, extent)

    # the parameters the reference distributions determine outright
    config = syn.EventConfig()
    config.pileup = args.pileup
    config.beamspotSigmaZ = target.z0_sigma
    config.d0Sigma = target.d0_sigma
    config.secondaryPtSlope = target.secondary_mean_pt - config.secondaryMinPt
    scale, exponent = fit_pt_spectrum(target.primary_pt, config.minPt)
    config.ptScale, config.ptExponent = scale, exponent
    print("determined directly: beamspotSigmaZ=%.1f d0Sigma=%.4f "
          "secondaryPtSlope=%.3f ptScale=%.3f ptExponent=%.3f"
          % (config.beamspotSigmaZ, config.d0Sigma, config.secondaryPtSlope,
             config.ptScale, config.ptExponent))

    # The yield and the secondary rate each shift the other's target - more
    # primaries mean more secondaries, and both leave space points - so they are
    # alternated. Each step is exact in its own parameter, so this settles at once
    # and the third round is only there to show that it has.
    span = config.maxEta - config.minEta
    config.chargedPerUnitEta = target.primaries / (args.pileup * span)
    for round_ in range(3):
        config = _with(config, {
            "chargedPerUnitEta": solve_charged_per_unit_eta(layout, config,
                                                            target)})
        config = _with(config, {
            "secondaryRate": solve_secondary_rate(layout, config, target)})
        print("    round %d: chargedPerUnitEta=%.3f secondaryRate=%.3f"
              % (round_, config.chargedPerUnitEta, config.secondaryRate))

    report(config, layout, target)

    name = ("itkPixelTtbarPu200" if args.detector == "itk"
            else "openDataDetectorTtbarPu200")
    print("\n" + as_cpp(config, name, provenance))


if __name__ == "__main__":
    main()
