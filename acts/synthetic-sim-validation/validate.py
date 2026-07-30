#!/usr/bin/env python3
"""Compare the ACTS synthetic space point generator against full-simulation MC.

The synthetic generator (`ActsFatras::Synthetic`) is a deliberately coarse fast
simulation built for seeding benchmarks. This checks that the distributions it
produces are in the right place, which is the only claim it makes.

Usage:

    # generate a fast-simulation event
    ActsBenchmarkSyntheticEventGeneration --runs 1 --warmup 0 --dump /tmp/fastsim

    # compare against an ITk full-simulation dump
    ./validate.py itk --fullsim <GNN4ITk dump>.root --fastsim /tmp/fastsim \\
        --events 5 -o plots

Everything is normalised per event, so the two samples are comparable whatever
number of events each holds.
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

FULL_STYLE = dict(color="#1f77b4", label="full sim")
FAST_STYLE = dict(color="#d62728", label="fast sim")


def _panel(ax, ax_ratio, full, fast, bins, xlabel, full_events, fast_events,
           logy=False):
    """One overlaid histogram with a ratio panel below it."""
    hf, edges = np.histogram(full, bins=bins)
    hg, _ = np.histogram(fast, bins=bins)
    centres = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)

    # per event and per unit of the x axis, so bin widths do not matter
    yf = hf / (full_events * widths)
    yg = hg / (fast_events * widths)

    ax.step(centres, yf, where="mid", **FULL_STYLE)
    ax.step(centres, yg, where="mid", **FAST_STYLE)
    ax.set_ylabel("per event / bin")
    # an empty sample cannot be log-scaled, and an empty panel is worth seeing
    if logy and (yf > 0).any() and (yg > 0).any():
        ax.set_yscale("log")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.25)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(yf > 0, yg / yf, np.nan)
    ax_ratio.axhline(1.0, color="black", lw=0.8)
    ax_ratio.step(centres, ratio, where="mid", color=FAST_STYLE["color"])
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


def plot_space_points(full, fast, outdir: Path) -> None:
    """Global positions and the occupancy map."""
    fig, axes = _figure(2, 3, "Space points")

    specs = [
        (full.sp_x, fast.sp_x, np.linspace(-350, 350, 100), "x [mm]", False),
        (full.sp_y, fast.sp_y, np.linspace(-350, 350, 100), "y [mm]", False),
        (full.sp_z, fast.sp_z, np.linspace(-3000, 3000, 120), "z [mm]", False),
        (np.hypot(full.sp_x, full.sp_y), np.hypot(fast.sp_x, fast.sp_y),
         np.linspace(0, 350, 100), "r [mm]", True),
        (np.arctan2(full.sp_y, full.sp_x), np.arctan2(fast.sp_y, fast.sp_x),
         np.linspace(-np.pi, np.pi, 64), "phi [rad]", False),
    ]
    for i, (a, b, bins, label, logy) in enumerate(specs):
        row, col = divmod(i, 3)
        _panel(*_pair(axes, row, col), a, b, bins, label,
               full.num_events, fast.num_events, logy=logy)

    # the last slot gets the total count per event instead of a distribution
    ax, ax_ratio = _pair(axes, 1, 2)
    ax.bar([0, 1], [len(full.sp_x) / full.num_events,
                    len(fast.sp_x) / fast.num_events],
           color=[FULL_STYLE["color"], FAST_STYLE["color"]])
    ax.set_xticks([0, 1], ["full sim", "fast sim"])
    ax.set_ylabel("space points per event")
    ax.grid(alpha=0.25, axis="y")
    ax_ratio.axis("off")

    fig.tight_layout()
    fig.savefig(outdir / "spacepoints.png", dpi=130)
    plt.close(fig)

    # r-z occupancy, side by side rather than overlaid
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharex=True, sharey=True)
    for ax, sample, name in ((axes[0], full, "full sim"),
                             (axes[1], fast, "fast sim")):
        r = np.hypot(sample.sp_x, sample.sp_y)
        ax.hist2d(sample.sp_z, r, bins=[np.linspace(-3000, 3000, 300),
                                        np.linspace(0, 350, 120)],
                  weights=np.full(len(r), 1.0 / sample.num_events),
                  norm=matplotlib.colors.LogNorm())
        ax.set_title(name)
        ax.set_xlabel("z [mm]")
    axes[0].set_ylabel("r [mm]")
    fig.suptitle("Space point occupancy")
    fig.tight_layout()
    fig.savefig(outdir / "occupancy_rz.png", dpi=130)
    plt.close(fig)


def plot_particles(full, fast, outdir: Path, primary: bool) -> None:
    """Kinematics of the primaries or of the secondaries."""
    name = "primaries" if primary else "secondaries"
    fmask = full.primary if primary else ~full.primary
    gmask = fast.primary if primary else ~fast.primary

    def f(field):
        return getattr(full, field)[fmask]

    def g(field):
        return getattr(fast, field)[gmask]

    specs = [
        ("eta", np.linspace(-4, 4, 80), "eta", False),
        ("phi", np.linspace(-np.pi, np.pi, 64), "phi [rad]", False),
        ("pt", np.logspace(-1, 1.5, 60), "pT [GeV]", True),
        ("d0", np.linspace(-5, 5, 80), "d0 [mm]", True),
        ("z0", np.linspace(-200, 200, 80), "z0 [mm]", False),
        ("num_hits", np.arange(-0.5, 20.5, 1.0), "pixel hits", False),
    ]
    if not primary:
        specs += [
            ("prod_r", np.linspace(0, 350, 80), "production r [mm]", True),
            ("prod_z", np.linspace(-3000, 3000, 100), "production z [mm]", False),
        ]

    ncols = 4
    nrows = (len(specs) + ncols - 1) // ncols
    fig, axes = _figure(nrows, ncols, name.capitalize())
    for i, (field, bins, label, logy) in enumerate(specs):
        row, col = divmod(i, ncols)
        ax, ax_ratio = _pair(axes, row, col)
        _panel(ax, ax_ratio, f(field), g(field), bins, label,
               full.num_events, fast.num_events, logy=logy)
        if field == "pt":
            ax.set_xscale("log")
            ax_ratio.set_xscale("log")
    for i in range(len(specs), nrows * ncols):
        row, col = divmod(i, ncols)
        for ax in _pair(axes, row, col):
            ax.axis("off")

    fig.tight_layout()
    fig.savefig(outdir / f"{name}.png", dpi=130)
    plt.close(fig)


def plot_hits_vs_eta(full, fast, outdir: Path) -> None:
    """Mean number of pixel hits per particle against eta."""
    bins = np.linspace(-4, 4, 41)
    centres = 0.5 * (bins[:-1] + bins[1:])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, primary in ((axes[0], True), (axes[1], False)):
        for sample, style in ((full, FULL_STYLE), (fast, FAST_STYLE)):
            mask = sample.primary if primary else ~sample.primary
            eta = sample.eta[mask]
            hits = sample.num_hits[mask]
            total, _ = np.histogram(eta, bins=bins, weights=hits)
            count, _ = np.histogram(eta, bins=bins)
            with np.errstate(divide="ignore", invalid="ignore"):
                mean = np.where(count > 0, total / count, np.nan)
            ax.step(centres, mean, where="mid", **style)
        ax.set_title("primaries" if primary else "secondaries")
        ax.set_xlabel("eta")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("mean pixel hits per particle")
    fig.suptitle("Hits per particle")
    fig.tight_layout()
    fig.savefig(outdir / "hits_vs_eta.png", dpi=130)
    plt.close(fig)


def summarise(full, fast) -> str:
    lines = ["", "%-26s %14s %14s %8s" % ("", "full sim", "fast sim", "ratio")]

    def row(label, a, b):
        ratio = b / a if a else float("nan")
        lines.append("%-26s %14.1f %14.1f %8.2f" % (label, a, b, ratio))

    row("space points/event",
        len(full.sp_x) / full.num_events, len(fast.sp_x) / fast.num_events)
    for label, mask_f, mask_g in (
        ("primaries/event", full.primary, fast.primary),
        ("secondaries/event", ~full.primary, ~fast.primary),
    ):
        row(label, mask_f.sum() / full.num_events, mask_g.sum() / fast.num_events)
        row("  mean pt [GeV]", full.pt[mask_f].mean(), fast.pt[mask_g].mean())
        row("  mean hits", full.num_hits[mask_f].mean(),
            fast.num_hits[mask_g].mean())
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="detector", required=True)

    itk = sub.add_parser("itk", help="compare against an ITk GNN4ITk dump")
    itk.add_argument("--fullsim", required=True, help="the dump ROOT file")
    itk.add_argument("--fastsim", required=True,
                     help="prefix the generator was dumped with")
    itk.add_argument("--events", type=int, default=5,
                     help="full-simulation events to read")
    itk.add_argument("-o", "--outdir", default="plots")

    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("reading %s ..." % args.fullsim)
    full = fullsim_itk.load(args.fullsim, num_events=args.events)
    print("  %d events, %d space points, %d particles"
          % (full.num_events, len(full.sp_x), len(full.pt)))

    print("reading %s_*.csv ..." % args.fastsim)
    fast = fastsim.load(args.fastsim)
    print("  %d events, %d space points, %d particles"
          % (fast.num_events, len(fast.sp_x), len(fast.pt)))

    print(summarise(full, fast))

    plot_space_points(full, fast, outdir)
    plot_particles(full, fast, outdir, primary=True)
    plot_particles(full, fast, outdir, primary=False)
    plot_hits_vs_eta(full, fast, outdir)

    print("\nwrote plots to %s/" % outdir)


if __name__ == "__main__":
    main()
