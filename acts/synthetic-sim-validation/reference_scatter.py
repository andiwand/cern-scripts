#!/usr/bin/env python3
"""Is a mismatch in a validation plot the model, or the reference's own noise?

    python dump_fastsim.py itk -o /tmp/fastsim-itk
    ./reference_scatter.py --fullsim ~/Downloads/'*DumpGNNITk_v9.root' \\
        --fastsim /tmp/fastsim-itk --events 5 --field z0

A five-event reference looks like a lot of statistics - forty thousand primaries
- and for some distributions it is not. A pile-up event holds about two hundred
interactions and some forty primaries share each interaction's vertex z
*exactly*, so a z0 histogram of five events has the statistics of a thousand
draws and not of forty thousand. Bin to bin that is a 15 to 30 % scatter in the
core, the size of a mismatch one would otherwise go looking for a cause of.

So this splits the dump files into subsamples of the size the comparison uses,
takes the bin-by-bin spread between them as the reference's own error, and
reports the fast simulation as a pull against it. A mean |pull| near one means
the model sits inside the reference's noise and there is nothing to explain.

It wants several files, one subsample per file, so the subsamples are
independent.
"""

from __future__ import annotations

import argparse
import glob

import numpy as np
import uproot

import fastsim
import fullsim_itk

#: Binning per field. All of them are per-particle.
FIELDS = {
    "z0": np.linspace(-200, 200, 41),
    "d0": np.logspace(-3, 1, 41),
    "eta": np.linspace(-4, 4, 41),
    "pt": np.logspace(-1, 1.5, 31),
    "num_hits": np.arange(-0.5, 20.5, 1.0),
}


def vertices_per_event(path: str, num_events: int) -> int:
    """How many distinct primary vertices an event of the dump holds.

    This, and not the particle count, is what the statistics of a z0 histogram
    is really set by.

    @param path one dump file
    @param num_events events to read
    @return the median over the events read
    """
    counts = []
    for batch in uproot.open(path)["GNN4ITk"].iterate(
            ["Part_vz", "Part_barcode"], entry_stop=num_events, step_size=1,
            library="np"):
        for i in range(len(batch["Part_vz"])):
            primary = batch["Part_barcode"][i] < fullsim_itk.PRIMARY_BARCODE_LIMIT
            counts.append(len(np.unique(np.round(batch["Part_vz"][i][primary],
                                                 4))))
    return int(np.median(counts)) if counts else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fullsim", nargs="+", required=True,
                        help="GNN4ITk dump files, one subsample per file")
    parser.add_argument("--fastsim", required=True,
                        help="prefix `dump_fastsim.py` was run with")
    parser.add_argument("--events", type=int, default=5,
                        help="events per subsample, i.e. what the comparison "
                             "being checked uses")
    parser.add_argument("--field", default="z0", choices=sorted(FIELDS))
    parser.add_argument("--secondaries", action="store_true",
                        help="check the secondary component instead")
    args = parser.parse_args()

    paths = sorted(p for pattern in args.fullsim for p in glob.glob(pattern))
    if len(paths) < 3:
        parser.error("needs at least three files to have a spread at all")
    bins = FIELDS[args.field]

    print("%d subsamples of %d events; %d distinct primary vertices per event"
          % (len(paths), args.events, vertices_per_event(paths[0], args.events)))

    histograms = []
    for path in paths:
        sample = fullsim_itk.load(path, num_events=args.events)
        wanted = ~sample.primary if args.secondaries else sample.primary
        values = getattr(sample, args.field)[wanted]
        histograms.append(np.histogram(values, bins=bins)[0]
                          / sample.num_events)
    histograms = np.array(histograms)
    mean, spread = histograms.mean(0), histograms.std(0, ddof=1)

    fast = fastsim.load(args.fastsim)
    wanted = ~fast.primary if args.secondaries else fast.primary
    model = np.histogram(getattr(fast, args.field)[wanted], bins=bins)[0] \
        / fast.num_events

    print("\n%22s %10s %10s %8s %8s %8s"
          % ("bin", "reference", "its rms", "as %", "model", "pull"))
    pulls = []
    for lo, hi, a, s, b in zip(bins[:-1], bins[1:], mean, spread, model):
        # a bin the reference barely fills has no meaningful spread either
        if a < 20:
            continue
        pull = (b - a) / s if s > 0 else np.nan
        pulls.append(pull)
        print("%10.4g..%10.4g %10.1f %10.1f %7.0f%% %8.1f %+8.2f"
              % (lo, hi, a, s, 100 * s / a, b, pull))

    pulls = np.array(pulls)
    print("\n  mean |pull| %.2f   chi2/ndf %.2f over %d bins"
          % (np.abs(pulls).mean(), np.mean(pulls ** 2), len(pulls)))
    print("  Around one means the model is inside the reference's own "
          "event-to-event\n  scatter, and the mismatch in the plot is that "
          "scatter rather than the model.")


if __name__ == "__main__":
    main()
