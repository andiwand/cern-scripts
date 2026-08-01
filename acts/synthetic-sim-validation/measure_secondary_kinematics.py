#!/usr/bin/env python3
"""Measure how the ITk dump's secondaries share their parent's momentum.

    ./measure_secondary_kinematics.py ~/Downloads/*DumpGNNITk_v9.root --events 5

This is where `secondaryKt`, `secondaryMomentumScale`, `secondaryMomentumExponent`
and `secondaryMomentumSpread` come from, measured rather than fitted. The ODD
preset carries the same numbers: the dump is the only reference with the parent
link this needs, ColliderML's record having none.

## The trap

`secondaryKt` is the Rayleigh *scale*, not its median (1.177 sigma) and not its
mean (1.253 sigma). Reading a median off the dump as a scale makes the opening
angle a fifth too wide. The scale is therefore reported three ways -- from the
median, from the mean, and as the maximum likelihood sqrt(<kT^2>/2) -- and their
agreement is the check that the distribution really is Rayleigh.

## Weighting

The measured scale grows with the parent, so one number for parents from 100 MeV
to tens of GeV depends on the weighting. An unweighted average over the dump's
secondaries leans towards hard parents, which are likelier to make a daughter
above its 300 MeV truth-link threshold. The generator's yield per crossing does
not depend on the parent, so take the crossing-weighted row.
"""

from __future__ import annotations

import argparse
import glob

import numpy as np
import uproot

TREE = "GNN4ITk"

#: Barcodes below this come from the generator. See `fullsim_itk.py`.
PRIMARY_BARCODE_LIMIT = 200_000

BRANCHES = ["Part_barcode", "Part_event_number", "Part_px", "Part_py",
            "Part_pz", "Part_pt", "Part_eta", "Part_charge", "Part_status",
            "Part_vParentBarcode", "Part_radius"]

#: Parent momentum bins in GeV, log-spaced enough to fit a power law over.
PARENT_BINS = np.array([0.0, 1.0, 2.0, 5.0, 10.0, np.inf])

#: Rayleigh: median / sigma and mean / sigma.
RAYLEIGH_MEDIAN = np.sqrt(2 * np.log(2))
RAYLEIGH_MEAN = np.sqrt(np.pi / 2)


def read(paths, num_events: int):
    """Every secondary whose parent is in the same record, against that parent.

    @param paths the dump files
    @param num_events events to read from each
    @return (kT, pL, parent p, daughter p, primary p), all in GeV
    """
    kt, pl, parent_p, daughter_p, primary_p = [], [], [], [], []
    for path in paths:
        for batch in uproot.open(path)[TREE].iterate(
                BRANCHES, entry_stop=num_events, step_size=1, library="np"):
            for i in range(len(batch["Part_pt"])):
                ev = {k: v[i] for k, v in batch.items()}
                _read_event(ev, kt, pl, parent_p, daughter_p)
                charged = ((ev["Part_barcode"] < PRIMARY_BARCODE_LIMIT)
                           & (np.abs(ev["Part_charge"]) > 0.5)
                           & (ev["Part_status"] == 1)
                           & (ev["Part_pt"] > 100.0)
                           & (np.abs(ev["Part_eta"]) < 4.0))
                primary_p.append(ev["Part_pt"][charged] / 1000.0
                                 * np.cosh(ev["Part_eta"][charged]))
    return (np.array(kt), np.array(pl), np.array(parent_p),
            np.array(daughter_p), np.concatenate(primary_p))


def _read_event(ev, kt, pl, parent_p, daughter_p) -> None:
    # The particle key is the (interaction, barcode) pair and not the barcode:
    # barcodes repeat across the interactions of one pile-up event. See the
    # traps section of the README.
    index = {(int(e), int(b)): j for j, (e, b)
             in enumerate(zip(ev["Part_event_number"], ev["Part_barcode"]))}
    momentum = np.stack([ev["Part_px"], ev["Part_py"], ev["Part_pz"]]) / 1000.0
    secondary = np.where((ev["Part_barcode"] >= PRIMARY_BARCODE_LIMIT)
                         & (np.abs(ev["Part_charge"]) > 0.5))[0]

    for j in secondary:
        # a secondary can carry several parent barcodes; the first one that
        # resolves within this event is its parent
        parent = None
        for link in np.atleast_1d(np.asarray(ev["Part_vParentBarcode"][j])):
            parent = index.get((int(ev["Part_event_number"][j]), int(link)))
            if parent is not None:
                break
        if parent is None:
            continue
        along_axis = momentum[:, parent]
        norm = float(np.linalg.norm(along_axis))
        if norm <= 0:
            continue
        daughter = momentum[:, j]
        along = float(daughter @ along_axis) / norm
        kt.append(float(np.linalg.norm(daughter - along * along_axis / norm)))
        pl.append(along)
        parent_p.append(norm)
        daughter_p.append(float(np.linalg.norm(daughter)))


def crossing_weights(parent_p: np.ndarray, spectrum) -> np.ndarray:
    """Re-weight the dump's secondaries onto the parents the generator has.

    The dump's secondary sample is a selection: only daughters above its truth
    link threshold are in it, and a hard parent makes those more often. The
    generator's yield per crossing does not depend on the parent, so each of its
    secondaries is drawn from the primary momentum spectrum instead. This
    reweights bin by bin onto that spectrum.

    @note One weight per primary rather than per crossing, a forward primary
          crossing more surfaces than a central one. The two differ by how the
          crossing count runs with momentum, which is weak next to the
          difference between the two spectra this corrects for.

    @param parent_p the parent momenta of the dump's secondaries, in GeV
    @param spectrum the momenta of the reference's primaries, in GeV
    @return one weight per secondary, normalised to one on average
    """
    edges = np.array([0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, np.inf])
    have = np.histogram(parent_p, bins=edges)[0].astype(float)
    want = np.histogram(spectrum, bins=edges)[0].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(have > 0, want / np.maximum(have, 1), 0.0)
    weight = ratio[np.clip(np.digitize(parent_p, edges) - 1, 0, len(ratio) - 1)]
    return weight / weight.mean() if weight.mean() > 0 else weight


def rayleigh_scales(kt: np.ndarray, weight=None):
    """The Rayleigh scale of a kT sample, the three ways it can be read off.

    @param kt the transverse kicks in GeV
    @param weight optional per-entry weights
    @return (from the median, from the mean, maximum likelihood)
    """
    if weight is None:
        weight = np.ones(len(kt))
    order = np.argsort(kt)
    cumulative = np.cumsum(weight[order])
    median = float(kt[order][np.searchsorted(cumulative,
                                             0.5 * cumulative[-1])])
    mean = float(np.average(kt, weights=weight))
    ml = float(np.sqrt(np.average(kt ** 2, weights=weight) / 2))
    return median / RAYLEIGH_MEDIAN, mean / RAYLEIGH_MEAN, ml


def momentum_power_law(pl: np.ndarray, parent_p: np.ndarray):
    """Fit `median pL = scale * p^power` to the dump.

    Through the medians of the parent bins rather than through the entries: the
    longitudinal momentum is log-normal about the median with a width of nearly
    two e-folds, so a fit to the entries measures the mean of a log-normal and
    not the median the generator draws about.

    @param pl the longitudinal momenta in GeV
    @param parent_p the parent momenta in GeV
    @return (scale in GeV, power, the per-bin medians as (parent, pL))
    """
    points = []
    for lo, hi in zip(PARENT_BINS[:-1], PARENT_BINS[1:]):
        band = (parent_p >= lo) & (parent_p < hi) & (pl > 0)
        if band.sum() < 50:
            continue
        points.append((float(np.median(parent_p[band])),
                       float(np.median(pl[band]))))
    parents, medians = np.array(points).T
    power, intercept = np.polyfit(np.log(parents), np.log(medians), 1)
    return float(np.exp(intercept)), float(power), points


def momentum_spread(pl: np.ndarray, parent_p: np.ndarray,
                    above: float = 5.0) -> float:
    """Width of the log-normal about that median, in e-folds.

    Measured above a parent momentum where the truncation at the parent does not
    bite: lower down the truncation narrows the distribution by itself, so a
    width measured there is the truncation's and not the model's.

    @param pl the longitudinal momenta in GeV
    @param parent_p the parent momenta in GeV
    @param above the parent momentum to measure over, in GeV
    @return half the 16-to-84 percentile spread of log(pL)
    """
    band = (parent_p >= above) & (pl > 0)
    lo, hi = np.percentile(np.log(pl[band]), [15.865, 84.135])
    return float((hi - lo) / 2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fullsim", nargs="+",
                        help="GNN4ITk dump files; several are worth reading, "
                             "the parent link needs both particles kept")
    parser.add_argument("--events", type=int, default=5,
                        help="events to read from each file")
    args = parser.parse_args()

    paths = sorted(p for pattern in args.fullsim for p in glob.glob(pattern))
    kt, pl, parent_p, daughter_p, primary_p = read(paths, args.events)
    print("%d files, %d secondaries with a resolved parent, %d primaries"
          % (len(paths), len(kt), len(primary_p)))

    print("\n=== transverse kick ===")
    print("%-24s %8s %10s %10s %10s"
          % ("parent p [GeV]", "n", "median kT", "mean kT", ""))
    print("%-24s %8s %10s %10s %10s"
          % ("", "", "sigma", "sigma", "sigma (ML)"))
    for lo, hi in zip(PARENT_BINS[:-1], PARENT_BINS[1:]):
        band = (parent_p >= lo) & (parent_p < hi)
        if band.sum() < 50:
            continue
        scales = rayleigh_scales(kt[band])
        print("%-24s %8d %10.3f %10.3f %10.3f"
              % ("%g - %g" % (lo, hi), band.sum(), *scales))
    flat = rayleigh_scales(kt)
    print("%-24s %8d %10.3f %10.3f %10.3f" % ("all, unweighted", len(kt),
                                              *flat))
    weight = crossing_weights(parent_p, primary_p)
    weighted = rayleigh_scales(kt, weight)
    print("%-24s %8d %10.3f %10.3f %10.3f"
          % ("all, on the primaries", len(kt), *weighted))

    print("\n=== longitudinal momentum ===")
    scale, power, points = momentum_power_law(pl, parent_p)
    print("  median pL against the parent's momentum:")
    for a, b in points:
        print("    parent %8.2f GeV   median pL %6.3f GeV" % (a, b))
    print("  power law through them: %.3f * p^%.3f" % (scale, power))
    spread = momentum_spread(pl, parent_p)
    print("  spread above 5 GeV: %.2f e-folds" % spread)

    # Whether the truncation at the parent is the right bound at all: a daughter
    # of a nuclear interaction can be released with more momentum than the
    # incident particle carried, and if the dump has many of those then bounding
    # the model's daughters is describing something the reference does not do.
    over = daughter_p > parent_p
    print("\n=== daughters harder than their parent ===")
    print("  %.1f%% of the dump's, median excess %.2f GeV"
          % (100 * over.mean(),
             float(np.median(daughter_p[over] - parent_p[over]))
             if over.any() else 0.0))

    # the three readings of the scale agree where the sample is Rayleigh, so
    # their mean is the value and their spread is the check on it
    kt_scale = float(np.mean(weighted))
    print("\n=== for `EventConfig`, in EventGenerator.hpp ===")
    print("  float secondaryMomentumScale = %.3f * Acts::UnitConstants::GeV;"
          % scale)
    print("  float secondaryMomentumExponent = %.3ff;" % power)
    print("  float secondaryMomentumSpread = %.2ff;" % spread)
    print("  float secondaryKt = %.3f * Acts::UnitConstants::GeV;  // +- %.3f"
          % (kt_scale, float(np.std(weighted))))


if __name__ == "__main__":
    main()
