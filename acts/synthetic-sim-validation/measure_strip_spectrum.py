#!/usr/bin/env python3
"""Measure what momenta the space points of an event come from, on both sides
of the comparison, and how many of them there are.

The strip layers sit where the soft tracks are gone: a 0.5 GeV track curls back
at r = 833 mm in a 2 T field, so the strip barrel is the part of the tracker
whose occupancy is *made* of the momentum spectrum rather than merely coloured
by it. If the generator's strip crossings are harder than the dump's, every
strip seeding number read off it is measured against the wrong sample.

    ./measure_strip_spectrum.py '~/Downloads/*DumpGNNITk_v9.root' --events 20

The dump is read at **space point** level, not cluster level. That distinction
is the whole measurement: a strip space point is a stereo pair, and the
crossings that fail to pair are preferentially the soft ones, so a cluster
spectrum is softer than the space point spectrum of the same event by
construction and comparing one against the other invents a discrepancy. The
`SP*` branches carry the pairing Athena actually made -- `SPCL2_index >= 0`
marks a strip pair, `SPisOverlap` separates the main collection from the three
overlap ones.

Momenta are quoted `--primary-only` by default, because that is the one
population both sides define the same way: only half the dump's clusters carry
a truth link at all, and the unlinked half is not a random half but the
secondaries it did not record.
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import uproot

TREE = "GNN4ITk"
PRIMARY_BARCODE_LIMIT = 200_000
BATCH_SIZE = 10

BRANCHES = [
    "SPCL1_index", "SPCL2_index", "SPisOverlap",
    "CLparticleLink_barcode", "CLparticleLink_eventIndex",
    "Part_event_number", "Part_barcode", "Part_pt",
]

#: Momenta the spectrum is quoted above, in GeV
THRESHOLDS = (0.1, 0.2, 0.5, 1.0, 2.0)


def _cluster_momentum(ev, primary_only: bool):
    """The momentum behind each cluster of one event.

    A cluster with several truth links is taken at the hardest of them, which is
    the particle a seeder would call it: the soft link is a delta ray riding
    along. One with no link reduces to NaN and drops out downstream.

    @param ev the dump's branches for one event
    @param primary_only keep only the links to a generator particle
    @return (pt per cluster with NaN where unlinked, whether each is primary)
    """
    import awkward as ak

    barcodes = ev["CLparticleLink_barcode"]
    indices = ev["CLparticleLink_eventIndex"]

    stride = np.int64(1) << 32
    part_key = (np.asarray(ev["Part_event_number"]).astype(np.int64) * stride
                + np.asarray(ev["Part_barcode"]).astype(np.int64))
    order = np.argsort(part_key)
    sorted_key = part_key[order]
    sorted_pt = np.asarray(ev["Part_pt"])[order] / 1000.0  # MeV -> GeV

    flat_barcode = np.asarray(ak.flatten(barcodes)).astype(np.int64)
    flat = (np.asarray(ak.flatten(indices)).astype(np.int64) * stride
            + flat_barcode)
    where = np.searchsorted(sorted_key, flat)
    inside = where < len(sorted_key)
    clamped = np.where(inside, where, 0)
    matched = inside & (sorted_key[clamped] == flat)
    if primary_only:
        matched &= flat_barcode < PRIMARY_BARCODE_LIMIT
    link_pt = np.where(matched, sorted_pt[clamped], np.nan)

    counts = np.asarray(ak.num(barcodes, axis=-1))
    pt = np.asarray(ak.fill_none(
        ak.max(ak.unflatten(link_pt, counts), axis=-1), np.nan))
    primary = np.asarray(ak.any(barcodes < PRIMARY_BARCODE_LIMIT, axis=-1))
    return pt, primary


def _fullsim_event(ev, kind: str, overlap: bool, primary_only: bool):
    """The momenta behind one event's space points of one kind.

    @param ev the dump's branches for one event
    @param kind "strip" or "pixel"
    @param overlap include the overlap space points, which have no counterpart
           in the generator
    @param primary_only keep only what a generator particle left
    @return (pt array, number of space points, number left by a primary)
    """
    cl1 = np.asarray(ev["SPCL1_index"])
    cl2 = np.asarray(ev["SPCL2_index"])
    # a pixel space point is one cluster, a strip space point a stereo pair
    selected = cl2 >= 0 if kind == "strip" else cl2 < 0
    if not overlap:
        selected &= np.asarray(ev["SPisOverlap"]) <= 0

    pt, primary = _cluster_momentum(ev, primary_only)
    first = pt[cl1[selected]]
    if kind == "strip":
        # the pair is one measurement; take the harder of the two clusters, and
        # keep it if either side knows what made it
        second = pt[cl2[selected]]
        got = np.fmax(np.nan_to_num(first, nan=-1.0),
                      np.nan_to_num(second, nan=-1.0))
        got = np.where(got < 0, np.nan, got)
        is_primary = primary[cl1[selected]] | primary[cl2[selected]]
    else:
        got = first
        is_primary = primary[cl1[selected]]
    return (got[np.isfinite(got)], int(selected.sum()), int(is_primary.sum()))


def fullsim(pattern: str, events: int, kind: str, overlap: bool,
            primary_only: bool):
    """Read the momentum behind every space point of a dump.

    @param pattern glob for the dump files
    @param events events to read, spread over the files
    @param kind "strip" or "pixel"
    @param overlap include the overlap space points
    @param primary_only keep only what a generator particle left
    @return (pt array, space points per event, primary share)
    """
    paths = sorted(glob.glob(os.path.expanduser(pattern)))
    if not paths:
        raise SystemExit(f"no files match {pattern}")
    per_file = max(1, events // len(paths))

    pt, total, primary, seen = [], 0, 0, 0
    for path in paths:
        if seen >= events:
            break
        with uproot.open(f"{path}:{TREE}") as tree:
            stop = min(per_file, tree.num_entries, events - seen)
            for batch in tree.iterate(BRANCHES, entry_start=0, entry_stop=stop,
                                      step_size=BATCH_SIZE, library="ak"):
                for i in range(len(batch)):
                    got, count, prim = _fullsim_event(
                        batch[i], kind, overlap, primary_only)
                    pt.append(got)
                    total += count
                    primary += prim
                    seen += 1
    return (np.concatenate(pt), total / max(1, seen),
            primary / max(1, total))


def fastsim(detector: str, events: int, pileup: int | None, kind: str,
            primary_only: bool):
    """The same off the generator, read through the Python bindings.

    @param detector a shipped detector name
    @param events events to generate
    @param pileup override for the preset's pile-up
    @param kind "strip" or "pixel"
    @param primary_only keep only what a primary left
    @return (pt array, space points per event, primary share)
    """
    import presets
    from acts.fatras import synthetic as syn

    layout = presets.layout(detector)
    config = presets.config(detector)
    if pileup is not None:
        config.generation.pileup = pileup

    pt, total, primary, base = [], 0, 0, config.seed
    for i in range(events):
        config.seed = base + i
        event = syn.generateEvent(layout, config)
        particles = event.particles
        which = np.asarray(event.stripParticleIds if kind == "strip"
                           else event.particleIds, dtype=np.int64)
        is_primary = np.asarray([particles[int(p)].primary for p in which],
                               dtype=bool)
        got = np.asarray([particles[int(p)].pt for p in which])
        pt.append(got[is_primary] if primary_only else got)
        total += len(which)
        primary += int(is_primary.sum())
    return (np.concatenate(pt) if pt else np.zeros(0),
            total / max(1, events), primary / max(1, total))


def report(name: str, pt, per_event: float, primary: float) -> None:
    """Print one side of the comparison.

    @param name what to call it
    @param pt the momenta behind its space points
    @param per_event space points per event
    @param primary share of them left by a primary
    """
    print(f"{name:>10}  per event {per_event:9.0f}   "
          f"primary {primary:6.1%}   sampled {len(pt):8d}")
    line = "   ".join(f">{t:g}: {float((pt > t).mean()):5.1%}" if len(pt)
                      else f">{t:g}:     -" for t in THRESHOLDS)
    print(f"{'':>12}{line}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fullsim", nargs="?",
                        help="glob for the dump; omitted measures the "
                             "generator alone")
    parser.add_argument("--detector", default="itk",
                        help="shipped detector to generate from")
    parser.add_argument("--events", type=int, default=10)
    parser.add_argument("--fastsim-events", type=int, default=None,
                        help="events to generate, defaulting to --events")
    parser.add_argument("--pileup", type=int, default=None)
    parser.add_argument("--kind", default="strip", choices=("strip", "pixel"))
    parser.add_argument("--overlap", action="store_true",
                        help="count the dump's overlap space points too, which "
                             "the generator does not make")
    parser.add_argument("--all-particles", action="store_true",
                        help="drop the primary-only restriction, which makes "
                             "the two sides count different populations")
    args = parser.parse_args()

    primary_only = not args.all_particles
    if args.fullsim:
        report("fullsim", *fullsim(args.fullsim, args.events, args.kind,
                                   args.overlap, primary_only))

    report("fastsim", *fastsim(args.detector,
                               args.fastsim_events or args.events,
                               args.pileup, args.kind, primary_only))


if __name__ == "__main__":
    main()
