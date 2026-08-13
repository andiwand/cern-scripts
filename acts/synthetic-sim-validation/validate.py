#!/usr/bin/env python3
"""Compare the ACTS synthetic space point generator against full-simulation MC.

The synthetic generator (`ActsFatras::Synthetic`) is a deliberately coarse fast
simulation built for seeding benchmarks. This checks that the distributions it
produces are in the right place, which is the only claim it makes.

Usage:

    # generate a fast-simulation event on the layout being validated
    ActsBenchmarkSyntheticEventGeneration --layout itk --runs 2 --warmup 0 \\
        --dump /tmp/fastsim-itk
    # or, with no benchmark built: ./dump_fastsim.py itk -o /tmp/fastsim-itk

    # compare against an ITk full-simulation dump
    ./validate.py itk --fullsim <GNN4ITk dump>.root --fastsim /tmp/fastsim-itk \\
        --events 5 -o plots

    # compare the ODD against ColliderML, downloaded from HuggingFace
    ./validate.py odd --fastsim /tmp/fastsim-odd --events 20 -o plots

Plots land in `<outdir>/<detector>/`, so the two detectors do not overwrite each
other. Everything is normalised per event, so the two samples are comparable
whatever number of events each holds.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fastsim
import fullsim_itk
import sample

FULL_STYLE = dict(color="#1f77b4", label="full sim")
FAST_STYLE = dict(color="#d62728", label="fast sim")


class Extent:
    """How far the pixel detector being validated reaches.

    The ITk pixel detector is more than twice the size of the ODD one in both
    directions, so a single set of axis ranges would leave one of the two
    comparisons squeezed into a corner of every plot.
    """

    def __init__(self, r_max: float, z_max: float) -> None:
        self.r_max = r_max
        self.z_max = z_max

    def r_bins(self, n: int = 100) -> np.ndarray:
        return np.linspace(0, self.r_max, n)

    def xy_bins(self, n: int = 100) -> np.ndarray:
        return np.linspace(-self.r_max, self.r_max, n)

    def z_bins(self, n: int = 120) -> np.ndarray:
        return np.linspace(-self.z_max, self.z_max, n)


#: ITk pixel: five barrel cylinders out to r = 291 mm, endcap disks to |z| = 2.8 m
ITK_EXTENT = Extent(r_max=350.0, z_max=3000.0)
#: ODD pixel: four barrel cylinders out to r = 170 mm, endcap disks to |z| = 1.5 m
ODD_EXTENT = Extent(r_max=200.0, z_max=1600.0)

#: Bands to compare the space point profiles on, one set per detector.
#:
#: Every band holds whole layers. A band narrower than that measures the
#: half-millimetre between the model's layer radius and the reference's cluster
#: positions instead of anything a model can change - the *primary* space points
#: scatter from 0.5 to 1.8 bin to bin on forty bins, and no secondary model
#: moves them. That noise is what made an earlier scan report the material term
#: as unconstrained: on forty bins the objective sits at 0.13 whatever the model
#: does, including for variants that differ by a factor two in the forward
#: region.
ITK_BANDS = (
    np.array([25.0, 60.0, 110.0, 150.0, 200.0, 250.0, 320.0]),
    np.array([0.0, 250.0, 500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0]),
)
ODD_BANDS = (
    np.array([25.0, 50.0, 90.0, 140.0, 200.0]),
    np.array([0.0, 300.0, 600.0, 700.0, 800.0, 900.0, 1050.0, 1200.0, 1400.0,
              1600.0]),
)

#: The impact parameter spans four decades and has to be plotted logarithmically:
#: the core of the luminous region is some 12 um wide while the displaced tail
#: reaches past a millimetre, so on a linear axis wide enough for the tail the
#: whole distribution lands in one bin, and on one narrow enough for the core the
#: tail is not there at all. Hence |d0| rather than d0 - it is symmetric anyway.
D0_BINS = np.logspace(-3, 1, 60)


def secondary_threshold(full) -> float:
    """The lowest secondary momentum the reference is able to report.

    A full simulation records a secondary only where its own truth machinery
    kept one, and the GNN4ITk dump keeps them above a hard 300 MeV: its lowest
    secondary sits at exactly 0.3000 GeV and nothing below it exists, which is
    why the raw counts differ by a factor eight while the space points agree to
    a percent. Comparing the model's secondaries down to `secondaryMinPt` -
    50 MeV - against that is comparing two different populations.

    So the threshold is read off the reference rather than assumed, and applied
    to both sides. For ColliderML it comes out at the loader's own 100 MeV cut
    and changes nothing, which is the point of measuring it.

    Space points are left alone. They are what they are whatever made them, and
    the dump's clusters carry the sub-threshold secondaries whether or not it
    tells us which particle they belong to.

    @param full the reference sample
    @return the threshold in GeV
    """
    secondary = ~full.primary
    return float(full.pt[secondary].min()) if secondary.any() else 0.0


def _particles(sample, primary: bool, threshold: float) -> np.ndarray:
    """The particle mask one of the two components is compared on.

    Hitless particles are already gone, every loader dropping them: a reference
    can only list what left a cluster. The model draws plenty, so its raw CSVs
    are not this population.
    """
    if primary:
        return sample.primary
    return (~sample.primary) & (sample.pt >= threshold)


def _errorbars(ax, x, y, error, color) -> None:
    """Draw error bars on a stepped line, without repeating it as markers."""
    ax.errorbar(x, y, yerr=error, fmt="none", ecolor=color, elinewidth=0.7,
                capsize=1.2, alpha=0.7)


def _panel(ax, ax_ratio, full, fast, bins, xlabel, full_events, fast_events,
           logy=False, normalise=False):
    """One overlaid histogram with a ratio panel below it.

    `normalise` compares the shapes instead of the rates, by dividing each
    histogram by its own total. It is for the distributions whose rate the
    reference cannot report - see `secondary_threshold` - where leaving the
    normalisation in pins every ratio panel at the top of its range and hides
    the only thing the panel could have shown.

    Error bars are `sqrt(n)` on the bin's entries. They are a floor rather than
    the truth: entries within an event are correlated, so a bin fed by a few
    busy tracks is noisier than this says.
    """
    hf, edges = np.histogram(full, bins=bins)
    hg, _ = np.histogram(fast, bins=bins)
    centres = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)

    # per event and per unit of the x axis, so bin widths do not matter
    scale_f = max(hf.sum(), 1) if normalise else full_events
    scale_g = max(hg.sum(), 1) if normalise else fast_events
    yf = hf / (scale_f * widths)
    yg = hg / (scale_g * widths)
    ef = np.sqrt(hf) / (scale_f * widths)
    eg = np.sqrt(hg) / (scale_g * widths)

    ax.step(centres, yf, where="mid", **FULL_STYLE)
    ax.step(centres, yg, where="mid", **FAST_STYLE)
    _errorbars(ax, centres, yf, ef, FULL_STYLE["color"])
    _errorbars(ax, centres, yg, eg, FAST_STYLE["color"])
    ax.set_ylabel("fraction / bin" if normalise else "per event / bin")
    # an empty sample cannot be log-scaled, and an empty panel is worth seeing
    if logy and (yf > 0).any() and (yg > 0).any():
        ax.set_yscale("log")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.25)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(yf > 0, yg / yf, np.nan)
        # the two samples are independent, so the relative errors add in
        # quadrature
        ratio_error = np.abs(ratio) * np.sqrt(
            np.where(hf > 0, 1.0 / hf, np.nan)
            + np.where(hg > 0, 1.0 / hg, np.nan))
    ax_ratio.axhline(1.0, color="black", lw=0.8)
    ax_ratio.step(centres, ratio, where="mid", color=FAST_STYLE["color"])
    _errorbars(ax_ratio, centres, ratio, ratio_error, FAST_STYLE["color"])
    ax_ratio.set_ylim(0, 2)
    ax_ratio.set_ylabel("fast / full", fontsize=7)
    ax_ratio.set_xlabel(xlabel)
    ax_ratio.grid(alpha=0.25)


def _figure(nrows, ncols, title):
    fig, axes = plt.subplots(
        2 * nrows, ncols,
        figsize=(4.2 * ncols, 3.6 * nrows),
        gridspec_kw={"height_ratios": [3, 1] * nrows},
        squeeze=False,
    )
    fig.suptitle(title)
    return fig, axes


def _pair(axes, row, col):
    return axes[2 * row][col], axes[2 * row + 1][col]


def _save(fig, outdir: Path, stem: str, fmt: str) -> None:
    """Write one figure, vector or raster depending on `fmt`."""
    fig.tight_layout()
    # dpi only bites on the raster formats; a PDF carries the curves themselves
    fig.savefig(outdir / f"{stem}.{fmt}", dpi=130)
    plt.close(fig)


def plot_space_points(full, fast, outdir: Path, extent: Extent, fmt: str) -> None:
    """Global positions and the occupancy map."""
    fig, axes = _figure(2, 3, "Space points")

    specs = [
        (full.sp_x, fast.sp_x, extent.xy_bins(), "x [mm]", False),
        (full.sp_y, fast.sp_y, extent.xy_bins(), "y [mm]", False),
        (full.sp_z, fast.sp_z, extent.z_bins(), "z [mm]", False),
        (np.hypot(full.sp_x, full.sp_y), np.hypot(fast.sp_x, fast.sp_y),
         extent.r_bins(), "r [mm]", True),
        (np.arctan2(full.sp_y, full.sp_x), np.arctan2(fast.sp_y, fast.sp_x),
         np.linspace(-np.pi, np.pi, 64), "phi [rad]", False),
    ]
    for i, (a, b, bins, label, logy) in enumerate(specs):
        row, col = divmod(i, 3)
        _panel(*_pair(axes, row, col), a, b, bins, label,
               full.num_events, fast.num_events, logy=logy)

    # the last slot gets the total count per event instead of a distribution
    ax, ax_ratio = _pair(axes, 1, 2)
    counts = np.array([len(full.sp_x), len(fast.sp_x)], dtype=float)
    events = np.array([full.num_events, fast.num_events], dtype=float)
    ax.bar([0, 1], counts / events, yerr=np.sqrt(counts) / events, capsize=3,
           ecolor="black", color=[FULL_STYLE["color"], FAST_STYLE["color"]])
    ax.set_xticks([0, 1], ["full sim", "fast sim"])
    ax.set_ylabel("space points per event")
    ax.grid(alpha=0.25, axis="y")
    ax_ratio.axis("off")

    _save(fig, outdir, "spacepoints", fmt)

    # r-z occupancy, side by side rather than overlaid
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharex=True, sharey=True)
    for ax, sample, name in ((axes[0], full, "full sim"),
                             (axes[1], fast, "fast sim")):
        r = np.hypot(sample.sp_x, sample.sp_y)
        _, _, _, mesh = ax.hist2d(
            sample.sp_z, r,
            bins=[extent.z_bins(300), extent.r_bins(120)],
            weights=np.full(len(r), 1.0 / sample.num_events),
            norm=matplotlib.colors.LogNorm(),
        )
        # tens of thousands of cells, which is worth rasterising in a PDF
        mesh.set_rasterized(True)
        ax.set_title(name)
        ax.set_xlabel("z [mm]")
    axes[0].set_ylabel("r [mm]")
    fig.suptitle("Space point occupancy")
    _save(fig, outdir, "occupancy_rz", fmt)


def plot_components(full, fast, outdir: Path, extent: Extent, fmt: str) -> None:
    """The space points split into the two components the generator models.

    The total is what `secondaryRate` is fitted to, so it agrees by
    construction and says nothing. This is where the model can be wrong and
    still look right: the primaries are short of the module overlaps and the
    curling tracks a helix cannot produce, and the non-primary component makes
    up the difference. Whether it makes it up *in the right place* is what these
    panels show.
    """
    fig, axes = _figure(2, 2, "Space points by component")
    specs = [
        (full.sp_primary, fast.sp_primary, "primary"),
        (~full.sp_primary, ~fast.sp_primary, "non-primary"),
    ]
    for row, (fmask, gmask, name) in enumerate(specs):
        for col, (values, bins, label, logy) in enumerate((
            ((np.hypot(full.sp_x, full.sp_y), np.hypot(fast.sp_x, fast.sp_y)),
             extent.r_bins(), "r [mm]", True),
            ((np.abs(full.sp_z), np.abs(fast.sp_z)),
             np.linspace(0, extent.z_max, 60), "|z| [mm]", False),
        )):
            ax, ax_ratio = _pair(axes, row, col)
            _panel(ax, ax_ratio, values[0][fmask], values[1][gmask], bins,
                   label, full.num_events, fast.num_events, logy=logy)
            ax.set_title("%s space points" % name, fontsize=9)
    _save(fig, outdir, "components", fmt)


def plot_particles(full, fast, outdir: Path, extent: Extent, fmt: str,
                   primary: bool, threshold: float) -> None:
    """Kinematics of the primaries or of the secondaries."""
    name = "primaries" if primary else "secondaries"
    fmask = _particles(full, primary, threshold)
    gmask = _particles(fast, primary, threshold)

    def value(sample, field, mask):
        # `abs_d0` is not a field of the sample, it is how d0 is plotted
        values = np.abs(sample.d0) if field == "abs_d0" else getattr(sample,
                                                                    field)
        return values[mask]

    def f(field):
        return value(full, field, fmask)

    def g(field):
        return value(fast, field, gmask)

    specs = [
        ("eta", np.linspace(-4, 4, 80), "eta", False),
        ("phi", np.linspace(-np.pi, np.pi, 64), "phi [rad]", False),
        ("pt", np.logspace(-1, 1.5, 60), "pT [GeV]", True),
        ("abs_d0", D0_BINS, "|d0| [mm]", True),
        ("z0", np.linspace(-200, 200, 80), "z0 [mm]", False),
        ("num_hits", np.arange(-0.5, 20.5, 1.0), "pixel hits", False),
    ]
    if not primary:
        specs += [
            ("prod_r", extent.r_bins(80), "production r [mm]", True),
            ("prod_z", extent.z_bins(100), "production z [mm]", False),
        ]

    ncols = 4
    nrows = (len(specs) + ncols - 1) // ncols
    title = name.capitalize()
    if not primary:
        # both sides are cut at it, so the plot has to say where it is, and the
        # rate is in the summary table rather than here
        title += (" (pT > %.2f GeV, the reference's own threshold; shapes, "
                  "normalised)" % threshold)
    fig, axes = _figure(nrows, ncols, title)
    for i, (field, bins, label, logy) in enumerate(specs):
        row, col = divmod(i, ncols)
        ax, ax_ratio = _pair(axes, row, col)
        _panel(ax, ax_ratio, f(field), g(field), bins, label,
               full.num_events, fast.num_events, logy=logy,
               normalise=not primary)
        if field in ("pt", "abs_d0"):
            ax.set_xscale("log")
            ax_ratio.set_xscale("log")
    for i in range(len(specs), nrows * ncols):
        row, col = divmod(i, ncols)
        for ax in _pair(axes, row, col):
            ax.axis("off")

    _save(fig, outdir, name, fmt)


def _mean_per_bin(eta, hits, bins):
    """The mean of `hits` in each eta bin, and the error on that mean.

    @return (mean, error), NaN where a bin holds no particle
    """
    total, _ = np.histogram(eta, bins=bins, weights=hits)
    total2, _ = np.histogram(eta, bins=bins, weights=hits.astype(float) ** 2)
    count, _ = np.histogram(eta, bins=bins)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = np.where(count > 0, total / count, np.nan)
        # the error on a mean, from the spread of the particles in the bin
        variance = np.where(count > 0, total2 / count - mean ** 2, np.nan)
        error = np.sqrt(np.maximum(variance, 0.0) / np.maximum(count, 1))
    return mean, error


def plot_hits_vs_eta(full, fast, outdir: Path, fmt: str,
                     threshold: float) -> None:
    """Mean number of pixel hits per particle against eta."""
    bins = np.linspace(-4, 4, 41)
    centres = 0.5 * (bins[:-1] + bins[1:])

    fig, axes = _figure(1, 2, "Hits per particle")
    for col, primary in ((0, True), (1, False)):
        ax, ax_ratio = _pair(axes, 0, col)
        means = {}
        for sample, style in ((full, FULL_STYLE), (fast, FAST_STYLE)):
            mask = _particles(sample, primary, threshold)
            mean, error = _mean_per_bin(sample.eta[mask],
                                        sample.num_hits[mask], bins)
            means[style["label"]] = (mean, error)
            ax.step(centres, mean, where="mid", **style)
            _errorbars(ax, centres, mean, error, style["color"])
        ax.set_title("primaries" if primary else "secondaries")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)

        (mf, ef), (mg, eg) = means[FULL_STYLE["label"]], means[FAST_STYLE["label"]]
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(mf > 0, mg / mf, np.nan)
            # the two samples are independent, so the relative errors add in
            # quadrature
            ratio_error = np.abs(ratio) * np.sqrt((ef / mf) ** 2 + (eg / mg) ** 2)
        ax_ratio.axhline(1.0, color="black", lw=0.8)
        ax_ratio.step(centres, ratio, where="mid", color=FAST_STYLE["color"])
        _errorbars(ax_ratio, centres, ratio, ratio_error, FAST_STYLE["color"])
        # tighter than the density panels': this is a mean rather than a count,
        # so it is never zero where either sample has particles at all and a
        # tenth either way is the scale the barrel deficit lives on
        ax_ratio.set_ylim(0.5, 1.5)
        ax_ratio.set_ylabel("fast / full", fontsize=7)
        ax_ratio.set_xlabel("eta")
        ax_ratio.grid(alpha=0.25)

    # primaries and secondaries on one scale, so the two panels can be read
    # against each other rather than only against the reference
    top = [_pair(axes, 0, col)[0] for col in (0, 1)]
    low = min(ax.get_ylim()[0] for ax in top)
    high = max(ax.get_ylim()[1] for ax in top)
    for ax in top:
        ax.set_ylim(low, high)
    top[0].set_ylabel("mean pixel hits per particle")
    _save(fig, outdir, "hits_vs_eta", fmt)


def plot_production_rz(full, fast, outdir: Path, extent: Extent, fmt: str,
                       threshold: float) -> None:
    """Where the secondaries are made, in r and z.

    The occupancy map says where the model *records*; this says where it
    *interacts*, which is the layout's material seen through the particle flux.
    A surface counted twice shows up here and nowhere else: it puts a line into
    the map and a spike into the radial profile at one radius, while the
    clusters it makes are spread over every layer downstream of it.

    The reference lists only the secondaries it kept truth for, so the rates are
    not comparable and the profiles are normalised. The *positions* are what
    this is for.
    """
    fmask = _particles(full, primary=False, threshold=threshold)
    gmask = _particles(fast, primary=False, threshold=threshold)

    # maps on top, then each profile over its own ratio panel
    fig = plt.figure(figsize=(11, 9))
    grid = fig.add_gridspec(3, 2, height_ratios=[3.0, 2.0, 1.0], hspace=0.32)
    maps = [fig.add_subplot(grid[0, c]) for c in range(2)]
    mains = [fig.add_subplot(grid[1, c]) for c in range(2)]
    ratios = [fig.add_subplot(grid[2, c], sharex=mains[c]) for c in range(2)]

    for ax, sample, mask, name in ((maps[0], full, fmask, "full sim"),
                                   (maps[1], fast, gmask, "fast sim")):
        _, _, _, mesh = ax.hist2d(
            sample.prod_z[mask], sample.prod_r[mask],
            bins=[extent.z_bins(300), extent.r_bins(150)],
            weights=np.full(int(mask.sum()), 1.0 / sample.num_events),
            norm=matplotlib.colors.LogNorm(),
        )
        mesh.set_rasterized(True)
        ax.set_title(name)
        ax.set_xlabel("production z [mm]")
        ax.set_ylabel("production r [mm]")

    # Fine bins on purpose: a doubled surface is a single-bin spike, and the
    # coarse bands the objective uses would average it away.
    for i, (field, bins, label) in enumerate(
            (("prod_r", extent.r_bins(300), "production r [mm]"),
             ("prod_z", extent.z_bins(300), "production |z| [mm]"))):
        a = getattr(full, field)[fmask]
        b = getattr(fast, field)[gmask]
        if field == "prod_z":
            a, b = np.abs(a), np.abs(b)
            bins = bins[bins >= 0]
        ha, edges = np.histogram(a, bins=bins)
        hb, _ = np.histogram(b, bins=bins)
        centres = 0.5 * (edges[:-1] + edges[1:])
        ya = ha / max(ha.sum(), 1)
        yb = hb / max(hb.sum(), 1)
        mains[i].step(centres, ya, where="mid", **FULL_STYLE)
        mains[i].step(centres, yb, where="mid", **FAST_STYLE)
        mains[i].set_yscale("log")
        mains[i].set_ylabel("fraction / bin")
        mains[i].legend(fontsize=7)
        mains[i].grid(alpha=0.25)
        mains[i].tick_params(labelbottom=False)

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(ya > 0, yb / ya, np.nan)
            error = np.abs(ratio) * np.sqrt(
                np.where(ha > 0, 1.0 / ha, np.nan)
                + np.where(hb > 0, 1.0 / hb, np.nan))
        ratios[i].axhline(1.0, color="black", lw=0.8)
        ratios[i].step(centres, ratio, where="mid", color=FAST_STYLE["color"])
        _errorbars(ratios[i], centres, ratio, error, FAST_STYLE["color"])
        ratios[i].set_ylim(0, 2)
        ratios[i].set_ylabel("fast / full", fontsize=7)
        ratios[i].set_xlabel(label)
        ratios[i].grid(alpha=0.25)

    fig.suptitle("Secondary production points (pT > %.2f GeV, shapes)"
                 % threshold)
    _save(fig, outdir, "production_rz", fmt)


def summarise(full, fast, threshold: float) -> str:
    lines = ["", "%-30s %14s %14s %8s" % ("", "full sim", "fast sim", "ratio")]

    def row(label, a, b):
        ratio = b / a if a else float("nan")
        lines.append("%-30s %14.1f %14.1f %8.2f" % (label, a, b, ratio))

    row("space points/event",
        len(full.sp_x) / full.num_events, len(fast.sp_x) / fast.num_events)
    # The total above and the components below are every space point either
    # sample holds: a seeder meets all of them, so that is the comparison. The
    # split is where the reference has to be read with care - it flags a cluster
    # primary from its truth link alone, and a twelfth of the ITk's come from a
    # primary below the generator's minPt or beyond its maxEta, which it cannot
    # make as primaries and produces as secondaries instead. That row is broken
    # out rather than hidden, being most of what is left of the primary deficit.
    row("  primary", full.sp_primary.sum() / full.num_events,
        fast.sp_primary.sum() / fast.num_events)
    row("    in the acceptance", full.sp_accepted.sum() / full.num_events,
        fast.sp_accepted.sum() / fast.num_events)
    row("    outside it", (full.sp_primary & ~full.sp_accepted).sum()
        / full.num_events,
        (fast.sp_primary & ~fast.sp_accepted).sum() / fast.num_events)
    row("  non-primary", (~full.sp_primary).sum() / full.num_events,
        (~fast.sp_primary).sum() / fast.num_events)
    for label, mask_f, mask_g in (
        ("primaries/event", _particles(full, True, threshold),
         _particles(fast, True, threshold)),
        ("secondaries/event (>%.2f GeV)" % threshold,
         _particles(full, False, threshold),
         _particles(fast, False, threshold)),
    ):
        row(label, mask_f.sum() / full.num_events, mask_g.sum() / fast.num_events)
        row("  mean pt [GeV]", full.pt[mask_f].mean(), fast.pt[mask_g].mean())
        row("  mean hits", full.num_hits[mask_f].mean(),
            fast.num_hits[mask_g].mean())
    # The secondary count is the one row here that is not like-for-like even
    # after the threshold, because the reference's secondary *list* is
    # incomplete where its clusters are not: half of the ITk dump's non-primary
    # clusters carry no truth link at all, so the particles behind them are
    # missing from this count while their clusters are in the non-primary row
    # above. Dividing those clusters by the mean hit count recovers a secondary
    # count the model can be held against; the raw ratio cannot.
    lines.append("(the reference lists only the secondaries it kept truth for; "
                 "compare non-primary space points, not the count)")
    return "\n".join(lines)


def _add_shared(parser: argparse.ArgumentParser, events: int) -> None:
    parser.add_argument("--fastsim", required=True,
                       help="prefix the generator was dumped with")
    parser.add_argument("--skip-events", type=int, default=0,
                        help="reference events to pass over first, so that the "
                             "validation sees different ones from the fit")
    parser.add_argument("--events", type=int, default=events,
                       help="full-simulation events to read")
    parser.add_argument("--cache-dir", default=".",
                        help="where to keep the reduced reference between runs; "
                             "empty to re-read it every time")
    parser.add_argument("-o", "--outdir", default="plots",
                       help="plots go into <outdir>/<detector>/")
    parser.add_argument("--format", default="pdf", choices=("pdf", "png", "svg"),
                       help="figure format")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="detector", required=True)

    itk = sub.add_parser("itk", help="compare against an ITk GNN4ITk dump")
    itk.add_argument("--fullsim", required=True, help="the dump ROOT file")
    _add_shared(itk, events=5)

    odd = sub.add_parser("odd", help="compare against ColliderML")
    odd.add_argument("--fullsim", default=None,
                     help="a downloaded ColliderML shard directory; the shard is "
                          "fetched from HuggingFace when this is left out")
    odd.add_argument("--channel", default="ttbar",
                     help="ColliderML physics channel")
    odd.add_argument("--pileup", default="pu200",
                     help="ColliderML pile-up variant, pu0 or pu200")
    _add_shared(odd, events=20)

    args = parser.parse_args()
    outdir = Path(args.outdir) / args.detector
    outdir.mkdir(parents=True, exist_ok=True)

    # The reference is the same from one run to the next while the fast
    # simulation being read against it is not, so it is reduced once and kept.
    cache = None
    if args.cache_dir:
        cache = (Path(args.cache_dir)
                 / ("sample-%s-%d+%d-v%d.npz"
                    % (args.detector, args.events, args.skip_events,
                       sample.CACHE_VERSION)))

    if args.detector == "itk":
        print("reading %s ..." % args.fullsim)
        full = sample.cached(cache, lambda: fullsim_itk.load(
            args.fullsim, num_events=args.events,
            skip_events=args.skip_events))
        extent = ITK_EXTENT
    else:
        def build_odd():
            # imported here so that the ITk path does not need parquet at all
            import fullsim_colliderml

            return fullsim_colliderml.load(
                channel=args.channel, pileup=args.pileup,
                num_events=args.events, skip_events=args.skip_events,
                local=args.fullsim)

        full = sample.cached(cache, build_odd)
        extent = ODD_EXTENT
    threshold = secondary_threshold(full)
    print("  %d events, %d space points, %d particles, secondaries above "
          "%.3f GeV" % (full.num_events, len(full.sp_x), len(full.pt),
                        threshold))

    print("reading %s_*.csv ..." % args.fastsim)
    fast = fastsim.load(args.fastsim)
    print("  %d events, %d space points, %d particles"
          % (fast.num_events, len(fast.sp_x), len(fast.pt)))

    print(summarise(full, fast, threshold))

    plot_space_points(full, fast, outdir, extent, args.format)
    plot_components(full, fast, outdir, extent, args.format)
    plot_particles(full, fast, outdir, extent, args.format, primary=True,
                   threshold=threshold)
    plot_particles(full, fast, outdir, extent, args.format, primary=False,
                   threshold=threshold)
    plot_production_rz(full, fast, outdir, extent, args.format, threshold)
    plot_hits_vs_eta(full, fast, outdir, args.format, threshold)

    print("\nwrote plots to %s/" % outdir)


if __name__ == "__main__":
    main()
