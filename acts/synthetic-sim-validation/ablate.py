#!/usr/bin/env python3
"""What each term of the synthetic model is worth, measured by removing it.

    ./ablate.py itk --fullsim <GNN4ITk dump>.root          # the quick scan
    ./ablate.py itk --fullsim <dump>.root --refit          # and the refits
    ./ablate.py itk --refit --only decays,turns            # a few of them

Two measurements per term, answering different questions:

  * The *quick* scan removes the term and re-solves only the two
    normalisations, so the space point count stays right. It says what the term
    carries where the fit currently sits.
  * The *refit* fits the whole model again without it. It says what survives
    once every other parameter has had the chance to absorb it, and that is
    what decides: a term the rest of the model can recover is a
    reparametrisation, not physics.

Where the two disagree the refit counts. Judge on all six figures at once (see
`fit_event_config.FIGURES`), never on the spatial shape alone: the terms trade
against each other, and dropping the transverse kick improves the spatial shape
threefold while wrecking the impact parameter distribution it exists for.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import numpy as np
from acts.fatras import synthetic as syn

import fit_event_config as fit


@dataclass(frozen=True)
class Term:
    """One term of the model, and how to take it out."""

    #: what to name it on the command line
    key: str
    #: what it does, for the table
    what: str
    #: `EventConfig` fields that switch it off. This is the whole of the term
    #: as far as generating goes, so the quick scan needs nothing else.
    off: dict = field(default_factory=dict)
    #: the same switch spelled as `fit_config` arguments, for the terms the fit
    #: takes as arguments. Only a refit needs these: they stop the fit from
    #: fitting a parameter that is no longer in the model.
    fit_off: dict = field(default_factory=dict)
    #: whether taking it out changes the layout rather than the configuration
    flat_material: bool = False
    #: an alternative form of a term rather than its removal, which is a
    #: different question - "was this worth changing to" rather than "is this
    #: worth having" - and so is reported apart
    alternative: bool = False


#: Every term that was added on top of the plain "helix from the beam line
#: crossing surfaces" model, in the order they went in.
TERMS = (
    Term("yield-profile", "the endcap yield profile",
         fit_off={"no_forward_material": True}, flat_material=True),
    Term("path-length", "yield weighted by the incidence angle",
         off={"maxDiscPathLength": 1.0, "maxCylinderPathLength": 1.0}, fit_off={"path_length": 1.0}),
    Term("turns", "the return branch of a curling track",
         off={"maxTurns": 0.5}, fit_off={"turns": 0.5}),
    Term("rapidity-edge", "the fall-off at the end of the rapidity plateau",
         off={"rapidityEdgeWidth": 0.0},
         fit_off={"no_rapidity_edge": True}),
    Term("decays", "neutral V0 decays away from a surface",
         off={"decayYield": 0.0}, fit_off={"no_decays": True}),
    Term("min-pt", "the floor under the secondary momentum",
         off={"secondaryMinPt": 1e-4}),
    # With no kick at all every secondary follows its parent exactly, so
    # nothing opens an impact parameter but curvature.
    Term("kick", "the transverse kick, and so the opening angle",
         off={"secondaryKt": 1e-3}),
    Term("parent-momentum", "the daughter's dependence on its parent",
         off={"secondaryMomentumExponent": 0.0}),
    Term("spread", "the width of the daughter momentum spectrum",
         off={"secondaryMomentumSpread": 0.05}),
    # Not a removal: the exponent set to one is the model this replaced, where a
    # daughter took a fixed *fraction* of its parent. Reported apart because
    # "is the exponent worth fitting" is not "is it worth having".
    Term("momentum-fraction", "a fixed fraction of the parent instead",
         off={"secondaryMomentumExponent": 1.0}, alternative=True),
)

#: The fit arguments the shipped preset of each detector was produced with.
#: `ablate.py` has to start from these or it would be scoring the preset
#: against a differently-fitted baseline rather than against itself.
BASELINE = {"itk": {"path_length": 4.0, "turns": 3.0},
            "odd": {"path_length": 4.0, "turns": 3.0}}

PRESET = {"itk": (syn.makeItkPixelLayout, syn.EventConfig.itkPixelTtbarPu200),
          "odd": (syn.makeOpenDataDetectorPixelLayout,
                  syn.EventConfig.openDataDetectorTtbarPu200)}


def flat_layout(description):
    """The same detector with every disc yielding alike.

    The material a layout carries is read off the geometry and is not this: the
    profile is the *surplus* a coarse forward disc has to make up for the rings
    it does not resolve. Flattening it leaves the material alone and removes
    that surplus.
    """
    syn.applyEndcapYieldProfile(description, 1e9, 1.0)
    return syn.makeLayout(description)


def quick(term: Term, config, layout, description, target):
    """Take a term out of a fitted configuration and re-solve the two
    normalisations.

    The two normalisations are re-solved because every profile is a shape and
    the comparison is meaningless against a model making the wrong number of
    space points. Nothing else is touched.

    @param term the term to remove
    @param config the fitted configuration
    @param layout the fitted layout
    @param description the layout description, for the terms that need a
           different layout
    @param target what to score against
    @return the scorecard
    """
    trial = fit._with(config, term.off)
    if term.flat_material:
        layout = flat_layout(description)
    trial = fit._with(trial, {"chargedPerUnitRapidity":
                              fit.solve_charged_per_unit_rapidity(layout, trial,
                                                             target)})
    trial = fit._with(trial, {"secondaryRate":
                              fit.solve_secondary_rate(layout, trial, target)})
    return fit.scorecard(trial, layout, target)


def refit(term: Term, detector: str, target, fullsim=None, events=None,
          cache_dir="."):
    """Fit the whole model again with a term taken out.

    A fresh description each time: the endcap material profile is fitted onto
    it in place, so reusing one would carry the previous term's fit into this
    one.

    @return (scorecard, config)
    """
    description, _, _ = fit.reference(detector, fullsim=fullsim, events=events,
                                      cache_dir=cache_dir)
    arguments = dict(BASELINE[detector])
    arguments.update(term.fit_off)
    config, layout, _ = fit.fit_config(description, target, overrides=term.off,
                                       verbose=False, **arguments)
    return fit.scorecard(config, layout, target), config


def header() -> str:
    """@return the column headings of the scorecard table"""
    return ("  %-22s" % "") + "".join("%9s" % h for _, h, _ in fit.FIGURES)


def row(label: str, card: dict) -> str:
    """@return one scored configuration as a table row"""
    return ("  %-22s" % label) + "".join(
        "%9.3f" % card[key] for key, _, _ in fit.FIGURES)


def noise(config, layout, target, seeds: int) -> dict:
    """The event-to-event spread of the untouched preset.

    Every figure is measured on a single generated event, so a term that moves
    one by less than this has not been shown to do anything.

    @param seeds how many events to score the untouched preset on
    @return the standard deviation of each figure over those events
    """
    cards = [fit.scorecard(fit._with(config, {"seed": 12345 + i}), layout,
                           target) for i in range(seeds)]
    return {key: float(np.std([c[key] for c in cards], ddof=1))
            for key, _, _ in fit.FIGURES}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("detector", choices=("itk", "odd"))
    parser.add_argument("--fullsim", default=None,
                        help="the ITk dump; unused for the ODD, which downloads")
    parser.add_argument("--events", type=int, default=None)
    parser.add_argument("--cache-dir", default=".")
    parser.add_argument("--refit", action="store_true",
                        help="refit the whole model without each term, which "
                             "takes minutes per term rather than seconds")
    parser.add_argument("--only", default=None,
                        help="comma-separated term keys, for a subset")
    parser.add_argument("--seeds", type=int, default=8,
                        help="events to measure the event-to-event spread of "
                             "the untouched preset on, which is the scale a "
                             "difference has to beat to mean anything")
    args = parser.parse_args()

    terms = TERMS
    if args.only:
        wanted = set(args.only.split(","))
        unknown = wanted - {t.key for t in TERMS}
        if unknown:
            parser.error("unknown term(s): %s" % ", ".join(sorted(unknown)))
        terms = tuple(t for t in TERMS if t.key in wanted)

    description, target, _ = fit.reference(args.detector, fullsim=args.fullsim,
                                           events=args.events,
                                           cache_dir=args.cache_dir)
    make_layout, make_config = PRESET[args.detector]
    config, layout = make_config(), make_layout()

    print("\nwhat each term is, and what taking it out means")
    for term in terms:
        print("  %-22s %s%s" % (term.key, "no " + term.what,
                                "  (an alternative, not a removal)"
                                if term.alternative else ""))

    print("\nquick scan: the term removed from the fitted preset, the primary "
          "yield\nand the secondary rate re-solved, everything else left alone")
    print("%s   (a mismatch wants 0, a ratio wants 1)" % header())
    print(row("the preset", fit.scorecard(config, layout, target)))
    if args.seeds > 1:
        print(row("+- over %d seeds" % args.seeds,
                  noise(config, layout, target, args.seeds)))
    for term in terms:
        # a fresh description per term: `flat_layout` fills the weights in place
        fresh, _, _ = fit.reference(args.detector, fullsim=args.fullsim,
                                    events=args.events, cache_dir=args.cache_dir)
        print(row(term.key, quick(term, config, layout, fresh, target)))

    if not args.refit:
        return

    print("\nrefit: the whole model fitted again without the term")
    print(header())
    base, base_config = refit(Term("baseline", "-"), args.detector, target,
                              args.fullsim, args.events, args.cache_dir)
    print(row("the preset, refitted", base))
    for term in terms:
        card, fitted = refit(term, args.detector, target, args.fullsim,
                             args.events, args.cache_dir)
        print(row(term.key, card))
        # the compensation is half the answer: a term the rest of the model can
        # absorb shows up as another parameter moving to take its place
        print("    %-18s rate=%.3f eta=%.3f decays=%.3f"
              % ("", fitted.secondaryRate, fitted.chargedPerUnitRapidity,
                 fitted.decayYield))


if __name__ == "__main__":
    main()
