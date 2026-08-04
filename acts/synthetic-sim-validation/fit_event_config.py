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
`Fatras/src/Synthetic/EventConfig.cpp`.
"""

from __future__ import annotations

import argparse
import pickle
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


#: The selection both reference loaders apply, and so the population the primary
#: count and the momentum spectrum are fitted against. The generator reaches
#: below and beyond it on purpose - a real event has those particles and they
#: leave clusters - so anything held up against the reference is cut back to this
#: first, or the fit pays for particles the reference never listed.
ACCEPTANCE_MIN_PT = 0.1
ACCEPTANCE_MAX_ABS_ETA = 4.0


def fit_pt_spectrum(pt: np.ndarray, min_pt: float = ACCEPTANCE_MIN_PT):
    """Fit `dN/dpT ~ pT (1 + pT/S)^-n` to a momentum spectrum.

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
        # survival of `dN/dpT ~ pT (1 + pT/scale)^-n`, i.e. `samplePt`
        v = 1.0 + x / scale
        return (v ** (2.0 - exponent) / (exponent - 2.0)
                - v ** (1.0 - exponent) / (exponent - 1.0))

    def objective(logs):
        scale, exponent = np.exp(logs)
        # below two the spectrum has no finite integral
        if exponent <= 2.01:
            return 1e6
        model = above(bins[:-1], scale, exponent) - above(bins[1:], scale,
                                                          exponent)
        model = np.maximum(model, 1e-12)
        model /= model.sum()
        residual = np.log(model[filled]) - np.log(data[filled])
        return (np.sum(weight[filled] * residual**2) / np.sum(weight[filled]))

    result = minimize(objective, np.log([1.0, 6.5]), method="Nelder-Mead",
                      options={"xatol": 1e-4, "fatol": 1e-10, "maxiter": 3000})
    return tuple(np.exp(result.x))


class Target:
    """What the fast simulation is being fitted to, all per event."""

    #: Bumped whenever a field is added or its meaning changes, so that a cache
    #: written by an older version is not silently reused. The reduction is what
    #: the whole fit sees of the reference, and a stale one is a fit against the
    #: wrong thing rather than a crash.
    VERSION = 8

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
        # The whole cluster count, deliberately. A seeder meets every cluster
        # the detector makes, so the occupancy is what the generator has to
        # reproduce, and taking any of it out would leave a generated event
        # thinner than a real one.
        self.space_points = len(full.sp_x) / full.num_events
        # What the secondary rates are therefore standing in for on top of the
        # secondaries: the clusters of primaries below the generator's minPt or
        # beyond its rapidity range, which it cannot make as primaries. A
        # twelfth of ITk's primary clusters and 3 % of all of them, so the rate
        # sits about 5 % above one that only had secondaries to account for.
        outside = int((full.sp_primary & ~full.sp_accepted).sum())
        self.unaccepted_space_points = outside / full.num_events

        # The non-primary space points on their own. Scoring the total instead
        # would score nothing: the rates are solved for the total, so a
        # model that puts its secondaries in the wrong place looks exactly like
        # one that does not.
        self.r_bands, self.z_bands = bands
        r = np.hypot(full.sp_x, full.sp_y)
        z = np.abs(full.sp_z)
        other = ~full.sp_primary
        self.other = self._profile(r[other], z[other], bands, full.num_events)
        self.primary_space_points = int(full.sp_accepted.sum()) / full.num_events

        # What fraction of the secondary space points come from a particle born
        # away from any surface, i.e. from a decay in the beam pipe vacuum. Only
        # the reference's *linked* secondaries carry a production point, so this
        # is their fraction rather than the whole non-primary component's.
        hits = full.num_hits[~primary].astype(float)
        inside = full.prod_r[~primary] < self.beam_pipe_radius
        self.decay_fraction = (hits[inside].sum() / hits.sum() if hits.sum()
                               else 0.0)

        # The momentum above which the reference knows its own secondaries at
        # all, and therefore the only range it can be compared with over.
        #
        # A full simulation links a cluster to a truth particle only above some
        # momentum, and for secondaries that threshold sits well inside the
        # range the generator produces: the ITk dump's is a hard 300 MeV, sharp
        # to the last digit, while its *primaries* reach down to the loader's
        # own 100 MeV cut. The reference's non-primary particles are therefore a
        # selection rather than a population, and the clusters of everything
        # below the threshold are precisely the unlinked half of the dump.
        #
        # So every per-particle secondary observable has to be taken above this
        # on both sides - see `reduce_event`. Comparing the generator's whole
        # secondary spectrum, which starts at `secondaryMinPt`, against a
        # 300 MeV selection is what used to drive the fitted secondary momentum
        # far above anything physical.
        #
        # The per-*cluster* profiles are a different matter and must not be cut:
        # they count the unlinked clusters too, which is exactly what makes them
        # the whole of the non-primary component rather than a selection.
        self.secondary_pt_threshold = (float(full.pt[~primary].min())
                                       if (~primary).any() else 0.0)

        # The secondary momentum spectrum is not fitted: an exponential cannot
        # follow the full simulation, whose secondaries reach ten GeV where the
        # generator's run out below two, and putting it in the objective made it
        # the only term that mattered. Its one parameter is the mean instead,
        # which is what an exponential has to offer.
        self.secondary_mean_pt = full.pt[~primary].mean()
        self.primary_pt = full.pt[primary]

        # The impact parameter of a secondary, weighted by the space points it
        # leaves, in decades. This is a property of the opening angle rather
        # than of the yield: a secondary emitted along its parent points back
        # at the beam line however far out it was made, and one emitted across
        # it does not. Only the reference's linked secondaries have a d0 at
        # all, so the unlinked clusters are out of this one - which also means
        # it carries the momentum threshold above, and d0 is strongly
        # correlated with momentum, a soft secondary curling where a hard one
        # does not. The model side is cut to match.
        self.d0_bands = np.array([0.0, 0.1, 1.0, 10.0, 100.0, np.inf])
        self.secondary_d0 = self._d0_profile(
            np.abs(full.d0[~primary]), full.num_hits[~primary].astype(float),
            self.d0_bands)

        # Where the secondaries are *made*, and how much each of them leaves.
        # Everything above is a space point profile, and a secondary made on the
        # outermost disc leaves one hit, so a large surplus of them barely moves
        # the clusters. The production profile counts them where they are born,
        # which is exactly where the material term acts, and the hit count says
        # whether they are the reference's secondaries or a swarm of stubs
        # standing in for them.
        #
        # Both carry the momentum threshold, being per-particle, and both are
        # shapes: the secondary *count* cannot be matched and is not meant to
        # be - see the module docstring.
        secondary = (~primary) & (full.pt >= self.secondary_pt_threshold)
        self.secondary_prod_z = self._shape(np.abs(full.prod_z[secondary]),
                                            self.z_bands)
        self.secondary_hits = (float(full.num_hits[secondary].mean())
                               if secondary.any() else 0.0)

        # Which way the secondaries came off, as against where they were made.
        # The difference between the two is the opening angle, so this is the
        # figure the transverse kick answers to together with |d0|. The parents
        # are forward-weighted, a forward primary crossing more surfaces than a
        # central one.
        #
        # Folded, the reference being symmetric, which halves the noise.
        self.eta_bands = np.linspace(0.0, 4.0, 9)
        self.secondary_eta = self._shape(np.abs(full.eta[secondary]),
                                         self.eta_bands)

        # Where the primaries went, which is the plateau the generator draws
        # them on seen through the `p/E` Jacobian and the acceptance. Finer
        # bands than the secondaries': this is a shape with structure in it -
        # flat centrally and falling away past |eta| = 2.5 - rather than a
        # broad weighting, and eight bands cannot resolve where the fall
        # starts. The reference has ten thousand primaries an event, so even at
        # twenty bands the noise is well under a percent.
        #
        # Taken inside the acceptance on both sides, like the primary counts:
        # beyond it the reference has nothing and the generator is not asked
        # for anything.
        self.primary_eta_bands = np.linspace(0.0, ACCEPTANCE_MAX_ABS_ETA, 21)
        accepted = primary & (full.pt > ACCEPTANCE_MIN_PT)
        self.primary_eta = self._shape(np.abs(full.eta[accepted]),
                                       self.primary_eta_bands)

    @staticmethod
    def _shape(values, bands) -> np.ndarray:
        counts = np.histogram(values, bins=bands)[0].astype(float)
        total = counts.sum()
        return counts / total if total else counts

    @staticmethod
    def _d0_profile(d0, weights, bands) -> np.ndarray:
        counts = np.histogram(d0, bins=bands, weights=weights)[0]
        total = counts.sum()
        return counts / total if total else counts

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
    pt = np.fromiter((p.pt for p in particles), np.float32, len(particles))
    all_eta = np.fromiter((p.eta for p in particles), np.float32,
                          len(particles))
    all_hits = np.fromiter((p.numHits for p in particles), np.int32,
                           len(particles))
    of_particle = np.asarray(event.particleIds, dtype=np.int64)
    other = ~primary[of_particle]
    # The generator reaches below the reference's threshold and beyond its eta,
    # so its primaries are cut back to that selection before being counted
    # against it. The non-primary component is not: the reference has all of it.
    accepted = (primary & (pt > ACCEPTANCE_MIN_PT)
                & (np.abs(all_eta) < ACCEPTANCE_MAX_ABS_ETA))

    # The reference cannot see a secondary below its truth-link threshold, so
    # neither may the model when the two are compared per particle. This is the
    # selection, not `~primary`; the space point profiles above stay on the
    # whole non-primary component. See `Target.secondary_pt_threshold`.
    secondary = (~primary) & (pt >= target.secondary_pt_threshold)

    hits = all_hits.astype(float)[secondary]
    # A surface secondary is produced *on* a surface, the innermost of which is
    # the beam pipe, so anything inside it came from a decay and the split is
    # exact here. In the reference it is only nearly so.
    inside = (np.fromiter((p.productionRadius for p in particles), np.float32,
                          len(particles))[secondary]
              < target.beam_pipe_radius)
    d0 = np.abs(np.fromiter((p.d0 for p in particles), np.float32,
                            len(particles))[secondary])
    sec_pt = pt[secondary]

    # Every loader keeps only particles that leave a space point, so the
    # reference's secondaries all have at least one hit and the model's are cut
    # the same way. It matters for the mean hit count below; the profiles above
    # are weighted by the hit count and drop a hitless secondary anyway.
    prod_z = np.abs(np.fromiter((p.productionZ for p in particles), np.float32,
                                len(particles))[secondary])
    eta = np.abs(all_eta[secondary])
    visible = hits > 0
    return {
        "space_points": float(count),
        "primary_space_points": float(accepted[of_particle].sum()),
        "primaries": float((accepted & (all_hits > 0)).sum()),
        "other": Target._profile(r[other], z[other], (target.r_bands,
                                                      target.z_bands), 1),
        "decay_fraction": (hits[inside].sum() / hits.sum() if hits.sum()
                           else 0.0),
        "secondary_d0": Target._d0_profile(d0, hits, target.d0_bands),
        "secondary_mean_pt": float(sec_pt.mean()) if len(sec_pt) else 0.0,
        "secondary_prod_z": Target._shape(prod_z[visible], target.z_bands),
        "secondary_eta": Target._shape(eta[visible], target.eta_bands),
        "secondary_hits": float(hits[visible].mean()) if visible.any() else 0.0,
        "primary_eta": Target._shape(np.abs(all_eta[accepted & (all_hits > 0)]),
                                     target.primary_eta_bands),
    }


def reduce_events(layout, config, target: Target, events: int = 1,
                  seed: int | None = None) -> dict:
    """Average the reduction over several generated events.

    One event is not enough to tell two candidate configurations apart: the
    mismatch numbers below carry a couple of percent of noise at that, which is
    more than the differences being resolved.

    @param layout the detector to generate on
    @param config the configuration to generate with
    @param target the reference, which fixes the binning
    @param events how many events to average over
    @param seed the seed to generate from, the configuration's own if None
    @return the averaged reduction
    """
    def add(into, value):
        # the reduction nests: the non-primary profile is keyed by axis
        if isinstance(value, dict):
            return {k: add(None if into is None else into[k], v)
                    for k, v in value.items()}
        value = np.asarray(value, float)
        return value if into is None else into + value

    def scale(value, factor):
        if isinstance(value, dict):
            return {k: scale(v, factor) for k, v in value.items()}
        return value / factor

    if seed is not None:
        config = _with(config, {"seed": seed})
    generator = syn.EventGenerator(layout, config)
    total = None
    for _ in range(max(1, events)):
        total = add(total, reduce_event(generator.generate(), target))
    return scale(total, float(max(1, events)))


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


def _production_mismatch(fast, target: Target) -> float:
    """Squared log-ratio of the secondary production profiles in |z|.

    Scored like the space point profiles, and the companion to them: they say
    where the secondary clusters end up and this says where the secondaries were
    made. The endcap material term acts on the second, and only the second tells
    a model that makes the reference's secondaries from one that makes many
    times as many one-hit stubs in the same place.
    """
    return _shape_mismatch(target.secondary_prod_z, fast["secondary_prod_z"])


def _eta_mismatch(fast, target: Target) -> float:
    """Squared log-ratio of the secondary |eta| profiles.

    The companion to `_production_mismatch`: that one says where the secondaries
    were made and this one which way they left. Only the opening angle separates
    the two, so this is what the transverse kick is fitted against.
    """
    return _shape_mismatch(target.secondary_eta, fast["secondary_eta"])


def _primary_eta_mismatch(fast, target: Target) -> float:
    """Squared log-ratio of the primary |eta| profiles.

    What the rapidity plateau is fitted against. Note it is not the plateau
    seen directly: a primary reaches this histogram through the `p/E` Jacobian,
    through the acceptance and through having to leave a space point at all, so
    the edge cannot be read off the reference's own `dN/dy` and pinned - the
    forward end of that measurement is itself cut by the reference's |eta| < 4.
    """
    return _shape_mismatch(target.primary_eta, fast["primary_eta"])


def _shape_mismatch(reference, model) -> float:
    """Squared log-ratio of two normalised profiles, band by band."""
    a = np.asarray(reference, dtype=float)
    b = np.asarray(model, dtype=float)
    both = (a > 0) & (b > 0)
    if not both.any():
        return 1e6
    a, b = a[both] / a[both].sum(), b[both] / b[both].sum()
    return float(np.mean(np.log(b / a) ** 2))


def _reduce(full, bands, beam_pipe) -> Target:
    """Build a `Target` and report the sample it came from."""
    print("full simulation: %d events, %d space points, %.0f%% of them "
          "primary, %.1f%% of them from a primary outside the acceptance"
          % (full.num_events, len(full.sp_x), 100 * full.sp_primary.mean(),
             100 * (full.sp_primary & ~full.sp_accepted).mean()))
    return Target(full, bands, beam_pipe)


def cached_target(path: Path, build):
    """Reduce the reference once and reuse it across runs.

    The reference samples are gigabytes and every parameter of the fit sees
    them only through the handful of profiles `Target` keeps, so loading them
    per run costs the memory of the whole dump to arrive at a few kilobytes.
    Running several fits at once on one machine is what makes that fatal.

    @param path where to keep the reduced reference
    @param build called to build it when the cache is cold
    @return the `Target`
    """
    # The fields are pickled rather than the object, so that the cache does not
    # depend on whether this module is `__main__` or imported under its name.
    if path.exists():
        with path.open("rb") as handle:
            target = Target.__new__(Target)
            target.__dict__.update(pickle.load(handle))
            print("reference from %s" % path)
            return target
    target = build()
    with path.open("wb") as handle:
        pickle.dump(target.__dict__, handle)
    print("reference reduced and cached to %s" % path)
    return target


def reference(detector: str, *, fullsim=None, events=None, cache_dir=".",
              skip_events=0):
    """The layout description and reduced reference of one detector.

    The bands the reference is profiled in are the detector's own, so the two
    belong together.

    @param detector "itk" or "odd"
    @param fullsim the ITk dump; the ODD downloads its own
    @param events how many reference events to reduce, None for the default
    @param skip_events how many to pass over first, so that a fit and the
           validation of it see different events
    @param cache_dir where the reduced reference is kept between runs
    @return (description, target, provenance)
    """
    import sample
    import sample
    import validate  # for the per-detector bands

    if detector == "itk":
        description = syn.itkPixelDescription()
        bands = validate.ITK_BANDS
        events = events or 5
        provenance = ("Fitted against %d events of a GNN4ITk ttbar pu200 dump."
                      % events)

        def load():
            import fullsim_itk
            return fullsim_itk.load(fullsim, num_events=events,
                                    skip_events=skip_events)
    else:
        description = syn.openDataDetectorPixelDescription()
        bands = validate.ODD_BANDS
        events = events or 20
        provenance = ("Fitted against %d events of ColliderML ttbar_pu200."
                      % events)

        def load():
            import fullsim_colliderml
            return fullsim_colliderml.load(num_events=events,
                                           skip_events=skip_events)

    # Two caches, one behind the other. The outer one is the reduction the fit
    # reads and is invalidated by `Target.VERSION`; the inner one is the loaded
    # dump, so a new reduction can be built without touching the gigabytes it
    # came from. `validate.py` writes the same file for the events it scores on,
    # so the two share whichever half they have in common.
    def build():
        raw = (Path(cache_dir) / ("sample-%s-%d+%d-v%d.npz"
                                  % (detector, events, skip_events,
                                     sample.CACHE_VERSION))
               if cache_dir else None)
        return _reduce(sample.cached(raw, load), bands,
                       description.beamPipeRadius)

    cache = Path(cache_dir) / ("target-%s-%d%s-v%d.pkl"
                               % (detector, events,
                                  "" if not skip_events else "+%d" % skip_events,
                                  Target.VERSION))
    return description, cached_target(cache, build), provenance


def _d0_mismatch(fast, target: Target) -> float:
    """Squared log-ratio of the hit-weighted secondary |d0| profiles.

    Scored like the spatial profiles and for the same reason: the decades of
    |d0| span two orders of magnitude in population, so a plain difference
    would see only the one that holds most of the secondaries.
    """
    a = np.asarray(target.secondary_d0, dtype=float)
    b = np.asarray(fast["secondary_d0"], dtype=float)
    both = (a > 0) & (b > 0)
    if not both.any():
        return 1e6
    return float(np.mean(np.log(b[both] / a[both]) ** 2))


#: Transverse kick scales to try in `solve_secondary_kick`, in GeV, spanning
#: the measured 0.21 by a factor three either way.
KICK_GRID = (0.13, 0.16, 0.20, 0.24, 0.30, 0.38, 0.48)


def solve_secondary_kick(layout, config, target: Target, seeds: int = 3,
                         kicks=None):
    """Find the kick that reproduces the secondary |d0| and |eta|.

    `secondaryKt` is how wide a daughter comes off its parent, and it fills the
    large-|d0| end. The kick reaches |d0| only through the opening angle it implies against the
    longitudinal momentum, so it cannot put a hard secondary at a wide angle or
    a soft one at a narrow one.

    Scored on |eta| as well as |d0|, the two pulling opposite ways: a narrow
    kick leaves every daughter on its parent, and the parents are
    forward-weighted because a forward primary crosses more surfaces than a
    central one. Scored on |d0| alone the fit lands below the value the dump
    measures.

    A seed-averaged grid rather than a local search: one event's |d0| mismatch
    varies by up to 0.04 between realisations at a fixed setting, as large as
    the differences being resolved, and a simplex contracts on that.

    @note The rate is re-solved at every grid point: a wider kick throws
          secondaries off the layout and so changes the space point count,
          while |d0| is scored as a *share* of the secondary space points.

    @param layout the detector to generate on
    @param config the configuration to start from
    @param target what to match
    @param seeds events to average each grid point over
    @param kicks the kick scales to try, `KICK_GRID` by default. Pass a single
           value to score a measured kick rather than fit one, which is what the
           shipped presets do: left free, the kick runs to the top of any grid it
           is given and pays for it in a secondary momentum this objective does
           not see.
    @return (secondaryKt, the mismatch at it)
    """
    best = config.secondaryKt
    best_score = float("inf")
    for kt in (KICK_GRID if kicks is None else kicks):
        trial = _with(config, {"secondaryKt": kt})
        # re-solved once per grid point rather than per seed: the rate is what
        # makes the count right, and it barely moves between realisations
        trial = _with(trial, solve_secondary_rate(layout, trial, target))
        scores = []
        for i in range(seeds):
            fast = reduce_event(
                syn.generateEvent(layout, _with(trial, {"seed": 4000 + i})),
                target)
            scores.append(_d0_mismatch(fast, target)
                          + _eta_mismatch(fast, target))
        score = float(np.mean(scores))
        if score < best_score:
            best, best_score = float(kt), score
    return best, best_score


def solve_secondary_momentum_scale(layout, config, target: Target) -> float:
    """Find the `secondaryMomentumScale` that reproduces the mean secondary
    momentum.

    The scale sets the median longitudinal momentum at a parent of one GeV, and
    the mean that comes out of it depends on which parents interact rather than
    on the primary spectrum alone - harder tracks cross more surfaces and get
    more chances. It is also compared only above the reference's truth-link
    threshold, so raising the scale both hardens the secondaries and moves more
    of them across the threshold, and the mean of what is left responds by less
    than the scale changes. Neither inverts in closed form, so it is iterated;
    the compression means the plain step under-corrects and cannot oscillate, it
    only wants more rounds than an exact inverse would.

    Note the ITk value is measured off the dump outright, so on that reference
    this is a cross-check rather than a fit.

    @param layout the detector to generate on
    @param config the configuration to start from
    @param target what to match
    @return the scale that lands on `target.secondary_mean_pt`
    """
    scale = config.secondaryMomentumScale
    for _ in range(10):
        trial = _with(config, {"secondaryMomentumScale": scale})
        fast = reduce_event(syn.generateEvent(layout, trial), target)
        have = fast["secondary_mean_pt"]
        if have <= 0:
            break
        scale *= target.secondary_mean_pt / have
    return scale


#: Where the rapidity plateau's edge is looked for, as (edge, width) grids in
#: units of rapidity. Coarse first and then a local refinement, the objective
#: being smooth in both. Bounded below by 2.6, inside which the reference's own
#: dN/dy is flat to a third of a percent; the upper end reaches well past
#: `maxRapidity` because the two trade - a distant edge with a wide fall is the
#: same shape inside the range as a nearer one with a sharp fall - and the
#: minimum has to be allowed to sit inside the grid rather than against it.
RAPIDITY_EDGES = np.arange(2.6, 5.61, 0.2)
RAPIDITY_WIDTHS = np.arange(0.1, 1.51, 0.1)


def solve_rapidity_edge(layout, config, target: Target, seeds: int = 3,
                        around=None):
    """Find the taper on the rapidity plateau that reproduces the primary |eta|.

    `dN/dy` is flat only centrally and the fragmentation region falls away, so a
    plateau held flat to `maxRapidity` puts several percent too many primaries
    beyond |eta| = 2.5 - where each of them leaves twice the clusters a central
    one does, which is why it is worth more than the count suggests.

    A grid rather than a solve: the two parameters trade against each other
    along a valley - a nearer edge with a wider fall looks much like a farther
    one with a sharper - so a step in either alone is not informative. It is
    cheap enough at this resolution, the objective needing one event per point.

    Averaged over several seeds. A single event moves the twenty bands of the
    profile by enough to pick the wrong point of a flat valley, and the whole
    difference between the best and the worst point of the neighbourhood is a
    couple of percent of the shape.

    @param layout the detector to generate on
    @param config the configuration to start from
    @param target what to match
    @param seeds how many events to average the objective over
    @param around a previous result to refine about, or None for the whole grid
    @return (edge, width, mismatch)
    """
    if around is None:
        edges, widths = RAPIDITY_EDGES, RAPIDITY_WIDTHS
    else:
        edge, width = around[0], around[1]
        edges = edge + np.array([-0.1, 0.0, 0.1])
        widths = np.maximum(width + np.array([-0.05, 0.0, 0.05]), 0.05)

    # A primary's own hits do not depend on the secondaries it makes, and the
    # profile counts nothing else, so the whole non-primary component is
    # switched off for the scan. It is nine tenths of the cost of an event and
    # none of this measurement.
    base = _with(config, {"secondaryElectronRate": 0.0,
                          "secondaryNuclearRate": 0.0, "stubRate": 0.0,
                          "decayYield": 0.0})

    best = None
    for edge in edges:
        for width in widths:
            score = 0.0
            for seed in range(seeds):
                trial = _with(base, {"rapidityEdge": float(edge),
                                     "rapidityEdgeWidth": float(width),
                                     "seed": config.seed + seed})
                score += _primary_eta_mismatch(
                    reduce_event(syn.generateEvent(layout, trial), target),
                    target)
            score /= seeds
            if best is None or score < best[2]:
                best = (float(edge), float(width), score)
    return best


def solve_charged_per_unit_rapidity(layout, config, target: Target) -> float:
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
    # inside the reference's own selection, the generator reaching past it
    with_hits = sum(1 for p in event.particles
                    if p.primary and p.numHits > 0
                    and p.pt > ACCEPTANCE_MIN_PT
                    and abs(p.eta) < ACCEPTANCE_MAX_ABS_ETA)
    if with_hits == 0:
        return config.chargedPerUnitRapidity
    return config.chargedPerUnitRapidity * target.primaries / with_hits


def solve_secondary_rate(layout, config, target: Target) -> dict:
    """Scale both secondary rates so that the space point count comes out right.

    The two are scaled together: which of them a crossing draws on follows from
    its material, and that ratio is measured rather than fitted. Only the level
    is free.

    The primary hits do not depend on the rate at all and only one generation of
    secondaries is produced, so the surface secondaries' hit count scales with
    it exactly. The decay secondaries do not, which is what the iteration below
    is for.

    @param layout the detector to generate on
    @param config the configuration, whose own rates are the reference point
           the extrapolation starts from
    @param target what to match
    @return the two rates that land on `target.space_points`
    """
    scale = 1.0

    def rates(factor):
        return {"secondaryElectronRate": config.secondaryElectronRate * factor,
                "secondaryNuclearRate": config.secondaryNuclearRate * factor}
    # A cascade makes the count grow faster than the rate - a secondary that is
    # itself allowed to interact contributes a term in rate squared - so the
    # plain step overshoots and can oscillate. Damping the exponent costs a few
    # iterations and converges either way.
    step = 1.0
    # The decay secondaries are a fixed number that does not scale with the
    # rate, so the count is affine in it rather than linear and one step
    # overshoots. It still converges geometrically, the decays being the
    # smaller part.
    for _ in range(6 if step == 1.0 else 10):
        trial = _with(config, rates(scale))
        summary = syn.summarize(syn.generateEvent(layout, trial), 1.0)
        if summary.secondaryHits == 0:
            break
        wanted = target.space_points - summary.primaryHits
        if wanted <= 0:
            # the primaries alone already overshoot, which curling can do
            return rates(0.0)
        scale *= (wanted / summary.secondaryHits) ** step
    return rates(scale)


def solve_decay_yield(layout, config, target: Target) -> float:
    """Find the `decayYield` that puts the right share of secondaries inside the
    beam pipe.

    Linear in the yield in the same way the secondary rates are, so one step.
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


def _with(config, values: dict):
    """Copy a configuration with some fields replaced.

    `EventConfig` has no copy constructor exposed, so the fields are carried over
    by hand. Only the ones this script touches are copied, which is why the base
    configuration has to be the one everything else is taken from.
    """
    out = syn.EventConfig()
    for name in ("pileup", "chargedPerUnitRapidity", "minPt", "ptScale",
                 "ptExponent", "minRapidity", "maxRapidity", "rapidityEdge",
                 "rapidityEdgeWidth", "beamspotSigmaZ", "d0Sigma",
                 "secondaryElectronRate", "secondaryNuclearRate",
                 "decayYield", "decayLength",
                 "secondaryMinPt", "secondaryMomentumScale",
                 "secondaryMomentumExponent", "secondaryMomentumSpread",
                 "secondaryKt",
                 "secondaryEvaporationFraction", "secondaryEvaporationScale",
                 "secondaryElectronScale",
                 "secondaryElectronExponent", "secondaryElectronSpread",
                 "secondaryElectronKt",
                 "maxDiscPathLength", "maxCylinderPathLength",
                 "materialScale", "overlapScale",
                 "multipleScattering",
                 "energyLoss", "energyLossModel", "particlePdg",
                 "maxEnergyLossFraction", "maxTurns",
                 "stubRate", "stubClusters", "stubReach",
                 "positionSmearing", "sensorThickness", "bFieldZ", "seed"):
        setattr(out, name, getattr(config, name))
    for name, value in values.items():
        # cast to whatever the field already is: `pileup` and `seed` are
        # integers, and pybind11 refuses a float for them
        setattr(out, name, type(getattr(out, name))(value))
    return out


#: What a configuration is judged on, as ``key -> (heading, ideal)``. A
#: mismatch is a squared log-ratio and wants to be zero; a ratio wants to be
#: one. Ordered as they are printed.
FIGURES = (("shape", "shape", 0.0),
           ("prod_z", "prod z", 0.0),
           ("sec_eta", "sec eta", 0.0),
           ("prim_eta", "prim eta", 0.0),
           ("d0", "|d0|", 0.0),
           ("space_points", "sp", 1.0),
           ("primary_sp", "prim sp", 1.0),
           ("decay_fraction", "decays", 1.0),
           ("secondary_pt", "sec pt", 1.0),
           ("secondary_hits", "sec hits", 1.0))


def scorecard(config, layout, target: Target) -> dict:
    """Every figure of merit of one configuration, in one pass.

    The four mismatches are shapes and the rest are ratios to the reference. All
    nine together, because the terms trade against each other and no one figure
    decides anything on its own.

    @param config the configuration to score
    @param layout the detector to generate on
    @param target what to score against
    @return the figures of merit, keyed as in `FIGURES`
    """
    fast = reduce_event(syn.generateEvent(layout, config), target)

    def ratio(have, want):
        return have / want if want else float("nan")

    return {
        "shape": _mismatch(fast, target),
        "prod_z": _production_mismatch(fast, target),
        "sec_eta": _eta_mismatch(fast, target),
        "prim_eta": _primary_eta_mismatch(fast, target),
        "d0": _d0_mismatch(fast, target),
        "space_points": ratio(fast["space_points"], target.space_points),
        "primary_sp": ratio(fast["primary_space_points"],
                            target.primary_space_points),
        "decay_fraction": ratio(fast["decay_fraction"], target.decay_fraction),
        "secondary_pt": ratio(fast["secondary_mean_pt"],
                              target.secondary_mean_pt),
        "secondary_hits": ratio(fast["secondary_hits"], target.secondary_hits),
    }


def fit_config(description, target: Target, *, pileup=200, no_decays=False,
               no_rapidity_edge=False, rapidity_edge=None,
               path_length=1.0, turns=0.5,
               fit_momentum=False, fit_kick=False, rounds=3, overrides=None,
               verbose=True):
    """Fit a configuration to a reference, and return it with its layout.

    Callable so that `ablate.py` can run the same fit with a term taken out.

    @param description the layout description, which is read as it stands: what
           a crossing yields is its material and its path length, and there is
           no weight on top of either to fit
    @param target what to fit to
    @param pileup number of interactions to generate
    @param no_decays drop the decay component
    @param no_rapidity_edge leave the rapidity plateau flat over the whole range
    @param rapidity_edge pin the plateau's edge to (edge, width) rather than
           fitting it
    @param path_length clamp on the incidence weighting of a *disc*; one
           disables it. The cylinder bound is `maxCylinderPathLength` and
           is left where the preset carries it: it is what makes a beam
           pipe produce evenly along z, not something to fit.
    @param turns turning angle to propagate through
    @param fit_momentum solve the secondary momentum scale for the mean
    @param fit_kick fit the transverse kick to |d0| and |eta|
    @param rounds passes over the alternating solves
    @param overrides fields to force after every solve, as a dict. This is what
           an ablation switches off with, and it is reapplied each round
           because a solve returns a fresh configuration.
    @param verbose print the value of every parameter as it settles
    @return (config, layout)
    """
    overrides = dict(overrides or {})

    config = syn.EventConfig()
    config.pileup = pileup
    config.beamspotSigmaZ = target.z0_sigma
    config.d0Sigma = target.d0_sigma
    # binned from the reference's own threshold, not the generator's: the
    # generator reaches below it and the reference lists nothing there
    scale, exponent = fit_pt_spectrum(target.primary_pt)
    config.ptScale, config.ptExponent = scale, exponent
    # Physics rather than a fit: K0S and Lambda are what decay at this distance,
    # cTau being 27 and 79 mm and the typical boost of order two. It cannot be
    # measured off the reference, whose sample of decays inside the beam pipe is
    # truncated at the beam pipe.
    config.decayLength = 60.0
    # Physics rather than a fit: the layout carries the radiation lengths, so
    # the configuration only says that they are taken as they are.
    config.materialScale = 1.0
    config.multipleScattering = True
    config.energyLoss = True
    config.energyLossModel = syn.EnergyLossModel.Mode
    if no_decays:
        config.decayYield = 0.0
    config.maxDiscPathLength = path_length
    config.maxTurns = turns
    config = _with(config, overrides)
    layout = syn.makeLayout(description)
    if verbose:
        print("determined directly: beamspotSigmaZ=%.1f d0Sigma=%.4f "
              "ptScale=%.3f ptExponent=%.3f"
              % (config.beamspotSigmaZ, config.d0Sigma,
                 config.ptScale, config.ptExponent))

    # The yield and the secondary rate each shift the other's target - more
    # primaries mean more secondaries, and both leave space points - so they are
    # alternated. Each step is exact in its own parameter, so this settles at
    # once and the later rounds are there to show that it has. The decay yield
    # comes after them because the shape it is a fraction of has to have
    # settled first.
    span = config.maxRapidity - config.minRapidity
    config.chargedPerUnitRapidity = target.primaries / (pileup * span)
    # The plateau's edge is fitted first in the round: it moves primaries from
    # the forward region into the central one, and every count below is taken
    # inside an acceptance those primaries cross.
    edge = rapidity_edge
    for round_ in range(rounds):
        if no_rapidity_edge:
            config = _with(config, {"rapidityEdgeWidth": 0.0})
        else:
            if rapidity_edge is None:
                # the whole grid once, its neighbourhood thereafter
                edge = solve_rapidity_edge(layout, config, target,
                                           around=edge)[:2]
            config = _with(config, {"rapidityEdge": edge[0],
                                    "rapidityEdgeWidth": edge[1]})
        config = _with(config, {
            "chargedPerUnitRapidity": solve_charged_per_unit_rapidity(
                layout, config, target)})
        # Off by default, the scale being measured off the dump's own
        # secondaries against their parents. Solving it instead trades the
        # non-primary shape for the mean momentum -- on the ITk it moves the
        # scale from the measured 0.632 to 0.369 and the shape mismatch from
        # 0.057 to 0.097 to buy 0.06 of the |d0| one -- so what it really
        # measures is that the model's spectrum above the reference's threshold
        # is not the reference's shape, which no setting of a scale fixes.
        if fit_momentum:
            config = _with(config, {
                "secondaryMomentumScale": solve_secondary_momentum_scale(
                    layout, config, target)})
        # Inside the loop and after the momentum scale, not once before it. The
        # kick only reaches |d0| through the opening angle it makes against the
        # longitudinal momentum, so the two cannot be fitted apart: at half the
        # momentum the same kick is twice the angle. The old free opening angle
        # could be, which is why it used to sit outside.
        if fit_kick and "secondaryKt" not in overrides:
            kt, _ = solve_secondary_kick(layout, config, target)
            config = _with(config, {"secondaryKt": kt})
        if not no_decays:
            config = _with(config, {
                "decayYield": solve_decay_yield(layout, config, target)})
        config = _with(config, solve_secondary_rate(layout, config, target))
        # Once more, because the rate above moves the surface secondaries that
        # the decay fraction is a fraction *of*, so solving the yield before it
        # leaves the fraction stale by as much as 15 % on the ODD.
        if not no_decays:
            config = _with(config, {
                "decayYield": solve_decay_yield(layout, config, target)})
            config = _with(config,
                           solve_secondary_rate(layout, config, target))
        # last, so that a term an ablation has switched off cannot be brought
        # back by a solve above -- `decayYield` is the one that would be
        config = _with(config, overrides)
        if verbose:
            print("    round %d: chargedPerUnitRapidity=%.3f rates=%.3f/%.3f "
                  "rapidityEdge=%.2f/%.2f decayYield=%.3f momentumScale=%.3f "
                  "kt=%.3f"
                  % (round_, config.chargedPerUnitRapidity,
                     config.secondaryElectronRate, config.secondaryNuclearRate,
                     config.rapidityEdge, config.rapidityEdgeWidth,
                     config.decayYield, config.secondaryMomentumScale,
                     config.secondaryKt))
    return config, layout


#: Seed offset of the events a fit is *reported* on, so that it is never scored
#: on the events it was fitted to.
REPORT_SEED_OFFSET = 9973


def report(config, layout, target: Target, events: int = 1) -> None:
    """Print what the fitted configuration produces next to the target."""
    fast = reduce_events(layout, config, target, events,
                         seed=config.seed + REPORT_SEED_OFFSET)
    print("\n%-28s %12s %12s %8s" % ("", "full sim", "fast sim", "ratio"))
    for label, a, b in (
        ("space points/event", target.space_points, fast["space_points"]),
        ("  primary", target.primary_space_points,
         fast["primary_space_points"]),
        ("  non-primary", target.space_points - target.primary_space_points,
         fast["space_points"] - fast["primary_space_points"]),
        ("primaries/event", target.primaries, fast["primaries"]),
        ("z0 sigma [mm]", target.z0_sigma, config.beamspotSigmaZ),
        ("d0 sigma [mm]", target.d0_sigma, config.d0Sigma),
        ("secondaries from a decay", target.decay_fraction,
         fast["decay_fraction"]),
        # both sides taken above the reference's truth-link threshold, which is
        # printed below because it is a property of the sample and not of the fit
        ("secondary mean pt [GeV]", target.secondary_mean_pt,
         fast["secondary_mean_pt"]),
        ("secondary mean hits", target.secondary_hits,
         fast["secondary_hits"]),
    ):
        print("%-28s %12.4f %12.4f %8.2f" % (label, a, b, b / a if a else
                                             float("nan")))
    print("%-28s %12.4f %12s" % ("  above a threshold of",
                                 target.secondary_pt_threshold, "GeV"))
    print("%-28s %12s %12.4f" % ("non-primary shape mismatch", "",
                                 _mismatch(fast, target)))
    print("%-28s %12s %12.4f" % ("secondary production |z|", "",
                                 _production_mismatch(fast, target)))
    print("%-28s %12s %12.4f" % ("secondary |eta| mismatch", "",
                                 _eta_mismatch(fast, target)))
    print("%-28s %12s %12.4f" % ("primary |eta| mismatch", "",
                                 _primary_eta_mismatch(fast, target)))
    print("%-28s %12s %12.4f" % ("secondary |d0| mismatch", "",
                                 _d0_mismatch(fast, target)))
    a = np.asarray(target.primary_eta, float)
    b = np.asarray(fast["primary_eta"], float)
    print("  primary |eta|: %s" % "  ".join(
        "%.1f %.2f" % (target.primary_eta_bands[i], b[i] / a[i])
        for i in range(len(a)) if a[i] > 0 and b[i] > 0))
    a = np.asarray(target.secondary_prod_z, float)
    b = np.asarray(fast["secondary_prod_z"], float)
    print("  secondary production |z|: %s" % "  ".join(
        "%.0f-%.0f %.2f" % (target.z_bands[i], target.z_bands[i + 1],
                            b[i] / a[i])
        for i in range(len(a)) if a[i] > 0 and b[i] > 0))
    names = ["<0.1", "0.1-1", "1-10", "10-100", ">100"]
    print("  secondary |d0| [mm], share of their space points")
    print("    %-10s %s" % ("full sim", "  ".join(
        "%s %.3f" % (n, v) for n, v in zip(names, target.secondary_d0))))
    print("    %-10s %s" % ("fast sim", "  ".join(
        "%s %.3f" % (n, v) for n, v in zip(names, fast["secondary_d0"]))))
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
    for field, fmt in (("chargedPerUnitRapidity", "%.2ff"),
                       ("ptScale", "%.3ff"),
                       ("ptExponent", "%.2ff"),
                       ("rapidityEdge", "%.2ff"),
                       ("rapidityEdgeWidth", "%.2ff"),
                       # "%.0ff" would print 50 as "50f", which is not a literal
                       ("beamspotSigmaZ", "%.0f.f"),
                       ("d0Sigma", "%.4ff"),
                       ("secondaryElectronRate", "%.3ff"),
                       ("secondaryNuclearRate", "%.3ff"),
                       ("decayYield", "%.3ff"),
                       ("secondaryElectronScale", "%.3ff"),
                       ("secondaryElectronExponent", "%.3ff"),
                       ("secondaryElectronSpread", "%.3ff"),
                       ("secondaryElectronKt", "%.3ff"),
                       ("secondaryMomentumScale", "%.3ff"),
                       ("secondaryMomentumExponent", "%.3ff"),
                       ("secondaryMomentumSpread", "%.3ff"),
                       ("secondaryKt", "%.3ff"),
                       ("secondaryEvaporationFraction", "%.3ff"),
                       ("secondaryEvaporationScale", "%.3ff"),
                       ("maxDiscPathLength", "%.2ff"),
                       ("maxCylinderPathLength", "%.2ff"),
                       ("materialScale", "%.3ff"),
                       ("overlapScale", "%.3ff"),
                       ("stubRate", "%.3ff"),
                       ("maxTurns", "%.2ff")):
        lines.append(("  config.%s = " + fmt + ";") % (field,
                                                       getattr(config, field)))
    # the toggles, which are not fitted but are spelled out by a preset
    lines.append("  config.multipleScattering = %s;"
                 % ("true" if config.multipleScattering else "false"))
    lines.append("  config.energyLoss = %s;"
                 % ("true" if config.energyLoss else "false"))
    lines.append("  config.energyLossModel = EnergyLossModel::%s;"
                 % str(config.energyLossModel).rsplit(".", 1)[-1])
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
    parser.add_argument("--cache-dir", default=".",
                        help="where the reduced reference is kept, so that "
                             "repeated fits do not reload the full sample")
    parser.add_argument("--no-decays", action="store_true",
                        help="drop the decay component and fit without it, to "
                             "see what it is worth")
    parser.add_argument("--skip-events", type=int, default=0,
                        help="reference events to pass over first, so that a "
                             "fit and the validation of it see different ones")
    parser.add_argument("--report-events", type=int, default=5,
                        help="fast-simulation events to average the report "
                             "over; one is too noisy to compare two fits")
    parser.add_argument("--no-rapidity-edge", action="store_true",
                        help="leave the rapidity plateau flat over the whole "
                             "generated range, as it was before the edge was "
                             "measured")
    parser.add_argument("--rapidity-edge", default=None, metavar="EDGE,WIDTH",
                        help="pin the plateau's edge and fit the rest around "
                             "it, instead of scanning for it")
    parser.add_argument("--path-length", type=float, default=1.0,
                        metavar="MAX",
                        help="weight the yield of a crossing of a disc by "
                             "its path length through it, clamped at MAX; one "
                             "leaves every crossing weighted alike. Cylinders "
                             "have a bound of their own in the preset")
    parser.add_argument("--turns", type=float, default=0.5,
                        help="turning angle to propagate through, in turns; "
                             "half stops a track at its outermost point")
    parser.add_argument("--fit-momentum", action="store_true",
                        help="solve the secondary momentum scale for the mean "
                             "secondary momentum, rather than keeping the "
                             "value measured off the ITk dump")
    parser.add_argument("--fit-kick", action="store_true",
                        help="fit the transverse kick to the secondary "
                             "impact parameter distribution, rather than "
                             "keeping the value measured off the ITk dump")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=X",
                        dest="overrides",
                        help="pin an `EventConfig` field and fit the rest "
                             "around it; repeatable. Pinning what `--fit-kick` "
                             "lands on and refitting is how the yields end up "
                             "consistent with it")
    args = parser.parse_args()

    overrides = {}
    for item in args.overrides:
        name, _, value = item.partition("=")
        overrides[name] = float(value)

    description, target, provenance = reference(
        args.detector, fullsim=args.fullsim, events=args.events,
        cache_dir=args.cache_dir, skip_events=args.skip_events)

    rapidity_edge = None
    if args.rapidity_edge is not None:
        edge, _, width = args.rapidity_edge.partition(",")
        rapidity_edge = (float(edge), float(width))

    config, layout = fit_config(
        description, target, pileup=args.pileup, no_decays=args.no_decays,
        no_rapidity_edge=args.no_rapidity_edge, rapidity_edge=rapidity_edge,
        path_length=args.path_length, turns=args.turns,
        fit_momentum=args.fit_momentum, fit_kick=args.fit_kick,
        overrides=overrides)

    report(config, layout, target, args.report_events)

    name = ("itkPixelTtbarPu200" if args.detector == "itk"
            else "openDataDetectorTtbarPu200")
    print("\n" + as_cpp(config, name, provenance))


if __name__ == "__main__":
    main()
