#!/usr/bin/env python3
"""Score the shipped presets against a reference, without refitting them.

`fit_event_config.py` prints this at the end of a fit, but a fit takes an hour
and the presets it produced are already in the source. This scores what is
shipped, which is also what `validate.py` plots.

    ./scorecard.py itk --fullsim ~/Downloads/'*DumpGNNITk_v9.root' --events 50
    ./scorecard.py odd --events 50
"""

from __future__ import annotations

import argparse

from acts.fatras import synthetic as syn

import ablate
import fit_event_config as fit

PRESET = {"itk": (syn.makeItkPixelLayout, syn.EventConfig.itkPixelTtbarPu200),
          "odd": (syn.makeOpenDataDetectorPixelLayout,
                  syn.EventConfig.openDataDetectorTtbarPu200)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("detector", choices=sorted(PRESET))
    parser.add_argument("--fullsim", default=None)
    parser.add_argument("--events", type=int, default=50)
    parser.add_argument("--skip-events", type=int, default=0)
    parser.add_argument("--cache-dir", default=".")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=X",
                        help="override a field before scoring")
    args = parser.parse_args()

    _, target, _ = fit.reference(args.detector, fullsim=args.fullsim,
                                 events=args.events,
                                 cache_dir=args.cache_dir,
                                 skip_events=args.skip_events)
    make_layout, make_config = PRESET[args.detector]
    # averaged over seeds: every figure is measured on one generated event and
    # the spread between realisations is as large as the differences that matter
    layout, config = make_layout(), make_config()
    overrides = {}
    for item in getattr(args, "set"):
        name, _, value = item.partition("=")
        overrides[name] = float(value)
    config = fit._with(config, overrides)
    cards = [fit.scorecard(fit._with(config, {"seed": 9973 + i}), layout, target)
             for i in range(5)]
    mean = {k: sum(c[k] for c in cards) / len(cards) for k in cards[0]}
    print(ablate.header())
    print(ablate.row(args.detector, mean))


if __name__ == "__main__":
    main()
