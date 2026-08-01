#!/usr/bin/env python3
"""What material profile the reference asks for, cell by cell.

    python dump_fastsim.py itk -o /tmp/fastsim-itk
    ./implied_material.py --fullsim ~/Downloads/'*DumpGNNITk_v9.root' \\
        --fastsim /tmp/fastsim-itk --events 5

The generator's yield at a crossing is `secondaryRate * materialWeight *
pathLength`. Divide the secondaries produced in a cell of (r, |z|) by the
*primary space points* in that cell - the crossings that made them - and what is
left is the yield per crossing, i.e. the material weight up to the overall
normalisation. Do it for both samples and the ratio is the factor the model's
weight is wrong by, cell by cell.

`fit_event_config.py` fits the two parameters of the profile; this says whether
the shape it fits is the right shape at all, and what the residual looks like
where it is not.

Both yields use the fast simulation's primaries as the flux, so the denominator
cancels out of the ratio and only its binning matters. Using the reference's
would put the model's primary hit deficit into a table about the secondary yield.

The path length weighting is inside the measured yield rather than divided out,
so a cell whose crossings are all at a shallow angle reads high. Do not read the
first column at large |z|: at r < 60 and |z| > 1500 there are almost no
crossings, and the few there are come in at the tangent.
"""

from __future__ import annotations

import argparse
import glob

import numpy as np
import uproot

TREE = "GNN4ITk"

#: See `fullsim_itk.py`.
PRIMARY_BARCODE_LIMIT = 200_000

BRANCHES = ["Part_barcode", "Part_event_number", "Part_pt", "Part_eta",
            "Part_charge", "Part_status", "Part_radius", "Part_vz",
            "CLhardware", "CLparticleLink_barcode",
            "CLparticleLink_eventIndex"]

#: Coarse enough that a cell holds whole layers, as `validate.ITK_BANDS` is and
#: for the same reason, but split more finely in |z| because the profile this
#: measures is a function of |z|.
Z_CELLS = np.array([0, 250, 400, 600, 800, 1000, 1200, 1500, 1800, 2100, 2400,
                    2700, 3000.])
R_CELLS = np.array([0, 60, 130, 200, 260, 330.])

#: Cells with fewer than this many entries on either side are left blank: the
#: ratio of two small counts says nothing and prints as a large number.
MIN_ENTRIES = 20


def read_reference(paths, num_events: int, min_pt: float):
    """Production points of the reference's secondaries that leave a cluster.

    @param paths the dump files
    @param num_events events to read from each
    @param min_pt the momentum threshold in GeV
    @return (r, z, number of events)
    """
    r, z, events = [], [], 0
    for path in paths:
        for batch in uproot.open(path)[TREE].iterate(
                BRANCHES, entry_stop=num_events, step_size=1, library="np"):
            for i in range(len(batch["Part_pt"])):
                ev = {k: v[i] for k, v in batch.items()}
                events += 1
                keep = _secondaries(ev, min_pt)
                r.append(ev["Part_radius"][keep])
                z.append(ev["Part_vz"][keep])
    return np.concatenate(r), np.concatenate(z), events


def _secondaries(ev, min_pt: float) -> np.ndarray:
    """The mask `fullsim_itk.load` would apply, restricted to secondaries."""
    is_pixel = np.asarray([str(h) for h in ev["CLhardware"]]) == "PIXEL"
    hits: dict[tuple[int, int], int] = {}
    for pixel, indices, barcodes in zip(is_pixel,
                                        ev["CLparticleLink_eventIndex"],
                                        ev["CLparticleLink_barcode"]):
        if not pixel:
            continue
        for index, barcode in zip(indices, barcodes):
            key = (int(index), int(barcode))
            hits[key] = hits.get(key, 0) + 1
    num_hits = np.array([hits.get((int(e), int(b)), 0) for e, b
                         in zip(ev["Part_event_number"], ev["Part_barcode"])])
    return ((ev["Part_barcode"] >= PRIMARY_BARCODE_LIMIT)
            & (np.abs(ev["Part_charge"]) > 0.5)
            & (ev["Part_pt"] > 1000.0 * min_pt)
            & (np.abs(ev["Part_eta"]) < 4.0)
            & (num_hits > 0))


def read_fastsim(prefix: str, min_pt: float):
    """The same from a generated event, plus the crossings that are the flux.

    @param prefix the path prefix `dump_fastsim.py` was run with
    @param min_pt the momentum threshold in GeV
    @return (secondary r, secondary z, primary space point r, its z)
    """
    particles = np.genfromtxt(prefix + "_particles.csv", delimiter=",",
                              names=True)
    keep = ((particles["primary"] < 0.5) & (particles["pt"] > min_pt)
            & (np.abs(particles["eta"]) < 4.0) & (particles["numHits"] > 0))
    space_points = np.genfromtxt(prefix + "_spacepoints.csv", delimiter=",",
                                 names=True)
    primary = space_points["primary"] > 0.5
    return (particles["productionRadius"][keep], particles["productionZ"][keep],
            space_points["r"][primary], space_points["z"][primary])


def cells(r, z, weight: float) -> np.ndarray:
    """Bin into the (|z|, r) cells above, per event."""
    return np.histogram2d(np.abs(z), r, bins=[Z_CELLS, R_CELLS])[0] * weight


def _print(title: str, table: np.ndarray, fmt: str) -> None:
    print("\n=== %s ===" % title)
    print("  |z| band   " + "".join("%12s" % ("r %.0f-%.0f" % (a, b))
                                    for a, b in zip(R_CELLS[:-1], R_CELLS[1:])))
    for i, (a, b) in enumerate(zip(Z_CELLS[:-1], Z_CELLS[1:])):
        row = "".join("  " + (fmt % v).rjust(10) if np.isfinite(v)
                      else " " * 12 for v in table[i])
        print("  %4.0f-%4.0f " % (a, b) + row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fullsim", nargs="+", required=True,
                        help="GNN4ITk dump files")
    parser.add_argument("--fastsim", required=True,
                        help="prefix `dump_fastsim.py` was run with")
    parser.add_argument("--events", type=int, default=5,
                        help="events to read from each dump file")
    parser.add_argument("--min-pt", type=float, default=0.3,
                        help="secondary momentum threshold in GeV; the dump "
                             "links no cluster to a secondary below 0.3")
    args = parser.parse_args()

    paths = sorted(p for pattern in args.fullsim for p in glob.glob(pattern))
    ref_r, ref_z, events = read_reference(paths, args.events, args.min_pt)
    fast_r, fast_z, flux_r, flux_z = read_fastsim(args.fastsim, args.min_pt)
    print("reference: %d events, %d secondaries;  fast: 1 event, %d "
          "secondaries, %d primary space points"
          % (events, len(ref_r), len(fast_r), len(flux_r)))

    reference = cells(ref_r, ref_z, 1.0 / events)
    model = cells(fast_r, fast_z, 1.0)
    flux = cells(flux_r, flux_z, 1.0)

    _print("reference secondaries per event", reference, "%.0f")
    _print("model secondaries per event", model, "%.0f")
    _print("primary space points per event, the flux", flux, "%.0f")

    with np.errstate(divide="ignore", invalid="ignore"):
        sparse = (model < MIN_ENTRIES) | (reference < MIN_ENTRIES / events)
        correction = np.where(sparse | (flux <= 0), np.nan, reference / model)
    # the overall factor is `secondaryRate`, which is solved for separately, so
    # what this table is about is the departure from it
    overall = reference.sum() / model.sum()
    _print("correction to materialWeight, normalised to the overall %.3f"
           % overall, correction / overall, "%.2f")
    print("\n  One means the profile is right in that cell. A trend along |z| "
          "is the\n  profile's shape; a trend along r is not something a "
          "weight per disc can\n  express at all, `materialWeight` being a "
          "property of the surface.")


if __name__ == "__main__":
    main()
