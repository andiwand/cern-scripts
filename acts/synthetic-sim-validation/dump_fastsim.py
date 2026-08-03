#!/usr/bin/env python3
"""Generate synthetic events and write the CSV pairs `validate.py` reads.

This is the fast-simulation half of the comparison. It generates from the
*preset* - `EventConfig::itkPixelTtbarPu200` and its ODD counterpart - rather
than from a configuration built up here, so that what gets validated is what a
user of the generator gets, tuning and all. `fit_event_config.py` is the other
way round: it builds a configuration from scratch and prints the preset that
should hold the result.

    ./dump_fastsim.py itk -o /tmp/fastsim-itk --events 20
    ./dump_fastsim.py odd -o /tmp/fastsim-odd --events 20

Generate as many as the reference has, or the fast-simulation line carries the
noise of a single event against a reference averaged over fifty.

`ActsBenchmarkSyntheticEventGeneration --dump` writes the same two files, and is
the faster route when it is built; this needs only the Python bindings.
"""

from __future__ import annotations

import argparse

from acts.fatras import synthetic as syn

LAYOUTS = {
    "itk": (syn.makeItkPixelLayout, syn.EventConfig.itkPixelTtbarPu200),
    "odd": (syn.makeOpenDataDetectorPixelLayout,
            syn.EventConfig.openDataDetectorTtbarPu200),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("detector", choices=sorted(LAYOUTS))
    parser.add_argument("-o", "--out", required=True,
                        help="prefix for `<out>_spacepoints.csv` and "
                             "`<out>_particles.csv`")
    parser.add_argument("--pileup", type=int, default=None,
                        help="override the preset's pile-up")
    parser.add_argument("--seed", type=int, default=None,
                        help="override the preset's random seed")
    parser.add_argument("--events", type=int, default=1,
                        help="events to generate, each from the seed after the "
                             "last, written as one numbered CSV pair each")
    args = parser.parse_args()

    make_layout, make_config = LAYOUTS[args.detector]
    layout = make_layout()
    config = make_config()
    if args.pileup is not None:
        config.pileup = args.pileup
    if args.seed is not None:
        config.seed = args.seed

    seed = config.seed
    for i in range(args.events):
        config.seed = seed + i
        # a single event keeps the unnumbered name it has always had
        prefix = args.out if args.events == 1 else "%s-%03d" % (args.out, i)

        event = syn.generateEvent(layout, config)
        summary = syn.summarize(event, config.minPt)
        print("%s: %d space points, %d primaries, %d secondaries"
              % (prefix, summary.spacePoints, summary.primaries,
                 summary.secondaries))

        syn.writeEventCsv(event, layout, prefix)

    print("wrote %d event(s) to %s*_spacepoints.csv and %s*_particles.csv"
          % (args.events, args.out, args.out))


if __name__ == "__main__":
    main()
