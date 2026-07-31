#!/usr/bin/env python3
"""Generate one synthetic event and write the CSV pair `validate.py` reads.

This is the fast-simulation half of the comparison. It generates from the
*preset* - `EventConfig::itkPixelTtbarPu200` and its ODD counterpart - rather
than from a configuration built up here, so that what gets validated is what a
user of the generator gets, tuning and all. `fit_event_config.py` is the other
way round: it builds a configuration from scratch and prints the preset that
should hold the result.

    ./dump_fastsim.py itk -o /tmp/fastsim-itk
    ./dump_fastsim.py odd -o /tmp/fastsim-odd

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
    args = parser.parse_args()

    make_layout, make_config = LAYOUTS[args.detector]
    layout = make_layout()
    config = make_config()
    if args.pileup is not None:
        config.pileup = args.pileup
    if args.seed is not None:
        config.seed = args.seed

    event = syn.generateEvent(layout, config)
    summary = syn.summarize(event, config.minPt)
    print("%s: %d space points, %d primaries, %d secondaries"
          % (args.detector, summary.spacePoints, summary.primaries,
             summary.secondaries))

    syn.writeEventCsv(event, layout, args.out)
    print("wrote %s_spacepoints.csv and %s_particles.csv" % (args.out, args.out))


if __name__ == "__main__":
    main()
