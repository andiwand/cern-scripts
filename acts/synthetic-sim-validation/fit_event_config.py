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

    #: How far inside the layout's beam pipe a production point has to be to
    #: count as a decay. The layout carries the beam pipe as one radius while
    #: the real one is a wall of finite thickness with its supports around it,
    #: and interactions in that wall are the largest single source of
    #: secondaries there - a fifth of the ITk's. Cutting at the nominal radius
    #: would count all of them as decays.
    INSIDE_BEAM_PIPE = 0.85

    def __init__(self, full, bands, beam_pipe_radius) -> None:
        primary = full.primary
        self.beam_pipe_radius = self.INSIDE_BEAM_PIPE * beam_pipe_radius
        self.num_events = full.num_events
        # the population the generator's primary list corresponds to
        self.primaries = primary.sum() / full.num_events
        self.z0_sigma = robust_sigma(full.z0[primary])
        self.d0_sigma = robust_sigma(full.d0[primary])
        self.space_points = len(full.sp_x) / full.num_events

        # The non-primary space points on their own. Scoring the total instead
        # would score nothing: `secondaryRate` is solved for the total, so a
        # model that puts its secondaries in the wrong place looks exactly like
        # one that does not.
        self.r_bands, self.z_bands = bands
        r = np.hypot(full.sp_x, full.sp_y)
        z = np.abs(full.sp_z)
        other = ~full.sp_primary
        self.other = self._profile(r[other], z[other], bands, full.num_events)
        self.primary_space_points = int(full.sp_primary.sum()) / full.num_events

        # What fraction of the secondary space points come from a particle born
        # away from any surface, i.e. from a decay in the beam pipe vacuum. Only
        # the reference's *linked* secondaries carry a production point, so this
        # is their fraction rather than the whole non-primary component's.
        hits = full.num_hits[~primary].astype(float)
        inside = full.prod_r[~primary] < self.beam_pipe_radius
        self.decay_fraction = (hits[inside].sum() / hits.sum() if hits.sum()
                               else 0.0)

        # The secondary momentum spectrum is not fitted: an exponential cannot
        # follow the full simulation, whose secondaries reach ten GeV where the
        # generator's run out below two, and putting it in the objective made it
        # the only term that mattered. Its one parameter is the mean instead,
        # which is what an exponential above `secondaryMinPt` has to offer.
        self.secondary_mean_pt = full.pt[~primary].mean()
        self.primary_pt = full.pt[primary]

    @staticmethod
    def _profile(r, z, bands, num_events) -> dict:
        r_bands, z_bands = bands
        return {"r": np.histogram(r, bins=r_bands)[0] / num_events,
                "z": np.histogram(z, bins=z_bands)[0] / num_events}


def reduce_event(event, target: Target) -> dict:
    """Reduce a generated event the same way the target was reduced."""
    space_points = event.spacePoints
    count = len(space_points)
    x = np.fromiter((sp.x for sp in space_points), np.float32, count)
    y = np.fromiter((sp.y for sp in space_points), np.float32, count)
    z = np.abs(np.fromiter((sp.z for sp in space_points), np.float32, count))
    r = np.hypot(x, y)

    particles = event.particles
    primary = np.fromiter((p.primary for p in particles), bool, len(particles))
    of_particle = np.asarray(event.particleIds, dtype=np.int64)
    other = ~primary[of_particle]

    hits = np.fromiter((p.numHits for p in particles), np.int32,
                       len(particles)).astype(float)[~primary]
    # A surface secondary is produced *on* a surface, the innermost of which is
    # the beam pipe, so anything inside it came from a decay and the split is
    # exact here. In the reference it is only nearly so.
    inside = (np.fromiter((p.productionRadius for p in particles), np.float32,
                          len(particles))[~primary]
              < target.beam_pipe_radius)
    return {
        "space_points": float(count),
        "primary_space_points": float((~other).sum()),
        "other": Target._profile(r[other], z[other], (target.r_bands,
                                                      target.z_bands), 1),
        "decay_fraction": (hits[inside].sum() / hits.sum() if hits.sum()
                           else 0.0),
        "secondary_hits": float(hits.sum()),
    }


def _mismatch(fast, target: Target) -> float:
    """Squared log-ratio of the non-primary profiles, band by band.

    The log is what makes this a shape comparison: a plain difference would be
    dominated by the innermost barrel layer, which holds an order of magnitude
    more space points than an endcap disc band. Only bands both samples fill
    enter, the layout being fixed - where one of them has no surface at all, no
    setting of these parameters can help.

    Each profile is normalised to its own total first, so it carries shape only;
    the count is matched by `solve_secondary_rate` rather than traded against it
    here.
    """
    total = 0.0
    for axis in ("r", "z"):
        a = np.asarray(target.other[axis], dtype=float)
        b = np.asarray(fast["other"][axis], dtype=float)
        both = (a > 0) & (b > 0)
        if not both.any():
            return 1e6
        a = a[both] / a[both].sum()
        b = b[both] / b[both].sum()
        total += np.mean(np.log(b / a) ** 2)
    return total / 2


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

    The primary hits do not depend on the rate at all and only one generation of
    secondaries is produced, so the surface secondaries' hit count scales with
    it exactly. The decay secondaries do not, which is what the iteration below
    is for.

    @param layout the detector to generate on
    @param config the configuration, whose own `secondaryRate` is the reference
           point the extrapolation starts from
    @param target what to match
    @return the rate that lands on `target.space_points`
    """
    rate = config.secondaryRate
    # The decay secondaries are a fixed number that does not scale with the
    # rate, so the count is affine in it rather than linear and one step
    # overshoots. It still converges geometrically, the decays being the
    # smaller part.
    for _ in range(6):
        trial = _with(config, {"secondaryRate": rate})
        summary = syn.summarize(syn.generateEvent(layout, trial), 1.0)
        if summary.secondaryHits == 0:
            break
        wanted = target.space_points - summary.primaryHits
        rate *= wanted / summary.secondaryHits
    return rate


def solve_decay_yield(layout, config, target: Target) -> float:
    """Find the `decayYield` that puts the right share of secondaries inside the
    beam pipe.

    Linear in the yield in the same way `secondaryRate` is, so one step. Note it
    is a *share* rather than a count: the reference's own count of secondaries
    is not something the generator reproduces, but the fraction of them born
    away from a surface is a property of the physics rather than of the
    bookkeeping.

    @param layout the detector to generate on
    @param config the configuration to start from
    @param target what to match
    @return the yield that lands on `target.decay_fraction`
    """
    fast = reduce_event(syn.generateEvent(layout, config), target)
    if fast["decay_fraction"] <= 0 or target.decay_fraction <= 0:
        return config.decayYield
    # the surface secondaries are the rest of the sample, so matching a fraction
    # rather than a count needs the ratio of the two odds
    odds = target.decay_fraction / (1 - target.decay_fraction)
    have = fast["decay_fraction"] / (1 - fast["decay_fraction"])
    return config.decayYield * odds / have


def fit_forward_material(layout, config, target: Target):
    """Fit the forward material term to the non-primary profiles.

    Two parameters against two banded profiles, with `secondaryRate` re-solved
    at every setting so that the count is never traded against the shape.

    @param layout the detector to generate on
    @param config the configuration to start from
    @param target what to match
    @return (forwardMaterialScale, forwardMaterialPower)
    """
    def objective(logs):
        scale, power = np.exp(logs)
        # below one the term is a cusp at z = 0 rather than a plateau, which is
        # not what a barrel looks like
        if power < 1.0 or scale < 100.0:
            return 1e6
        trial = _with(config, {"forwardMaterialScale": scale,
                               "forwardMaterialPower": power})
        trial = _with(trial, {"secondaryRate": solve_secondary_rate(
            layout, trial, target)})
        return _mismatch(reduce_event(syn.generateEvent(layout, trial), target),
                         target)

    result = minimize(objective, np.log([config.forwardMaterialScale,
                                         config.forwardMaterialPower]),
                      method="Nelder-Mead",
                      options={"xatol": 1e-3, "fatol": 1e-6, "maxiter": 200})
    return tuple(np.exp(result.x))


def _with(config, values: dict):
    """Copy a configuration with some fields replaced.

    `EventConfig` has no copy constructor exposed, so the fields are carried over
    by hand. Only the ones this script touches are copied, which is why the base
    configuration has to be the one everything else is taken from.
    """
    out = syn.EventConfig()
    for name in ("pileup", "chargedPerUnitEta", "minPt", "ptScale",
                 "ptExponent", "minEta", "maxEta", "beamspotSigmaZ", "d0Sigma",
                 "secondaryRate", "forwardMaterialScale",
                 "forwardMaterialPower", "decayYield", "decayLength",
                 "secondaryMinPt", "secondaryPtSlope",
                 "secondaryOpeningAngle",
                 "positionSmearing", "sensorThickness", "bFieldZ", "seed"):
        setattr(out, name, getattr(config, name))
    for name, value in values.items():
        setattr(out, name, float(value))
    return out


def report(config, layout, target: Target) -> None:
    """Print what the fitted configuration produces next to the target."""
    fast = reduce_event(syn.generateEvent(layout, config), target)
    print("\n%-28s %12s %12s %8s" % ("", "full sim", "fast sim", "ratio"))
    for label, a, b in (
        ("space points/event", target.space_points, fast["space_points"]),
        ("  primary", target.primary_space_points,
         fast["primary_space_points"]),
        ("  non-primary", target.space_points - target.primary_space_points,
         fast["space_points"] - fast["primary_space_points"]),
        ("primaries/event", target.primaries, float(config.numPrimaries())),
        ("z0 sigma [mm]", target.z0_sigma, config.beamspotSigmaZ),
        ("d0 sigma [mm]", target.d0_sigma, config.d0Sigma),
        ("secondaries from a decay", target.decay_fraction,
         fast["decay_fraction"]),
    ):
        print("%-28s %12.4f %12.4f %8.2f" % (label, a, b, b / a if a else
                                             float("nan")))
    print("%-28s %12s %12.4f" % ("non-primary shape mismatch", "",
                                 _mismatch(fast, target)))
    for axis, bands in (("r", target.r_bands), ("z", target.z_bands)):
        a = np.asarray(target.other[axis], float)
        b = np.asarray(fast["other"][axis], float)
        both = (a > 0) & (b > 0)
        an, bn = a / a[both].sum(), b / b[both].sum()
        print("  non-primary %s: %s" % (axis, "  ".join(
            "%.0f-%.0f %.2f" % (bands[i], bands[i + 1], bn[i] / an[i])
            for i in range(len(bands) - 1) if both[i])))


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
                       ("forwardMaterialScale", "%.0f.f"),
                       ("forwardMaterialPower", "%.2ff"),
                       ("decayYield", "%.3ff"),
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
    parser.add_argument("--no-decays", action="store_true",
                        help="drop the decay component and fit without it, to "
                             "see what it is worth")
    parser.add_argument("--no-forward-material", action="store_true",
                        help="drop the forward material term, for a reference "
                             "that does not constrain it")
    args = parser.parse_args()

    import validate  # for the per-detector bands

    if args.detector == "itk":
        import fullsim_itk

        full = fullsim_itk.load(args.fullsim, num_events=args.events or 5)
        layout = syn.makeItkPixelLayout()
        bands = validate.ITK_BANDS
        beam_pipe = syn.itkPixelDescription().beamPipeRadius
        provenance = "Fitted against five events of a GNN4ITk ttbar pu200 dump."
    else:
        import fullsim_colliderml

        full = fullsim_colliderml.load(num_events=args.events or 20)
        layout = syn.makeOpenDataDetectorPixelLayout()
        bands = validate.ODD_BANDS
        beam_pipe = syn.openDataDetectorPixelDescription().beamPipeRadius
        provenance = ("Fitted against twenty events of ColliderML "
                      "ttbar_pu200.")

    print("full simulation: %d events, %d space points, %.0f%% of them primary"
          % (full.num_events, len(full.sp_x), 100 * full.sp_primary.mean()))
    target = Target(full, bands, beam_pipe)

    # the parameters the reference distributions determine outright
    config = syn.EventConfig()
    config.pileup = args.pileup
    config.beamspotSigmaZ = target.z0_sigma
    config.d0Sigma = target.d0_sigma
    config.secondaryPtSlope = target.secondary_mean_pt - config.secondaryMinPt
    scale, exponent = fit_pt_spectrum(target.primary_pt, config.minPt)
    config.ptScale, config.ptExponent = scale, exponent
    # Physics rather than a fit: K0S and Lambda are what decay at this distance,
    # cTau being 27 and 79 mm and the typical boost of order two. It cannot be
    # measured off the reference, whose sample of decays inside the beam pipe is
    # truncated at the beam pipe.
    config.decayLength = 60.0
    if args.no_decays:
        config.decayYield = 0.0
    if args.no_forward_material:
        config.forwardMaterialScale = 0.0
    print("determined directly: beamspotSigmaZ=%.1f d0Sigma=%.4f "
          "secondaryPtSlope=%.3f ptScale=%.3f ptExponent=%.3f"
          % (config.beamspotSigmaZ, config.d0Sigma, config.secondaryPtSlope,
             config.ptScale, config.ptExponent))

    # The yield and the secondary rate each shift the other's target - more
    # primaries mean more secondaries, and both leave space points - so they are
    # alternated. Each step is exact in its own parameter, so this settles at
    # once and the later rounds are there to show that it has. The forward
    # material term is fitted inside the loop because it moves the count too,
    # and the decay yield after it because the shape it is a fraction of has to
    # have settled first.
    span = config.maxEta - config.minEta
    config.chargedPerUnitEta = target.primaries / (args.pileup * span)
    for round_ in range(3):
        config = _with(config, {
            "chargedPerUnitEta": solve_charged_per_unit_eta(layout, config,
                                                            target)})
        if not args.no_forward_material:
            scale, power = fit_forward_material(layout, config, target)
            config = _with(config, {"forwardMaterialScale": scale,
                                    "forwardMaterialPower": power})
        if not args.no_decays:
            config = _with(config, {
                "decayYield": solve_decay_yield(layout, config, target)})
        config = _with(config, {
            "secondaryRate": solve_secondary_rate(layout, config, target)})
        print("    round %d: chargedPerUnitEta=%.3f secondaryRate=%.3f "
              "forwardMaterialScale=%.0f forwardMaterialPower=%.2f "
              "decayYield=%.3f"
              % (round_, config.chargedPerUnitEta, config.secondaryRate,
                 config.forwardMaterialScale, config.forwardMaterialPower,
                 config.decayYield))

    report(config, layout, target)

    # what the two new terms are worth, each measured by taking it back out and
    # re-solving the rate for the count it was carrying
    print("\nnon-primary shape mismatch, term by term")
    for label, fields in (("fitted", {}),
                          ("without the decays", {"decayYield": 0.0}),
                          ("without the forward material",
                           {"forwardMaterialScale": 0.0}),
                          ("without either", {"decayYield": 0.0,
                                              "forwardMaterialScale": 0.0})):
        trial = _with(config, fields)
        trial = _with(trial, {"secondaryRate": solve_secondary_rate(
            layout, trial, target)})
        print("  %-30s %.4f"
              % (label, _mismatch(reduce_event(syn.generateEvent(layout, trial),
                                               target), target)))

    name = ("itkPixelTtbarPu200" if args.detector == "itk"
            else "openDataDetectorTtbarPu200")
    print("\n" + as_cpp(config, name, provenance))


if __name__ == "__main__":
    main()
