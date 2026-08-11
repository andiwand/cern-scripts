#!/usr/bin/env python3
"""Turn the ROOT files written by `run.py` into a PDF.

Resolution is the width of the iterative +-3 sigma Gaussian core fit the
performance writer already puts in the file as `reswidth_<param>_vs_eta`, and
the bias is its mean. `--estimator quantile` instead takes the half width of
the central 68.27% interval off the residual histogram, which is insensitive to
how the fit range is chosen and covers the eta bins where the fit fails.
"""

from pathlib import Path

import argparse
import re

import numpy as np
import uproot
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# blue, orange, aqua, violet - validated for colour vision deficiency on all
# pairs, plus a marker shape each so the identity never rests on colour alone
VARIANTS = {
    "truth_all": ("truth seed, all space points", "#2a78d6", "o"),
    "truth_inner3": ("truth seed, 3 innermost", "#eb6834", "s"),
    "truth_spread3": ("truth seed, 3 spread", "#1baf7a", "^"),
    "triplet": ("triplet seeding", "#4a3aa7", "D"),
}

PARAMS = {
    "d0": ("$d_0$", "mm"),
    "z0": ("$z_0$", "mm"),
    "qopt_rel": ("$q/p_\\mathrm{T}$ (relative)", None),
}

MIN_ENTRIES = 25
QUANTILES = (0.158655, 0.5, 0.841345)


def resolutionVsEta(hist, estimator="fit"):
    """Resolution, its error and the bias per eta bin, plus the entry count."""
    etaEdges, resEdges, counts, width, widthErr, mean = hist

    eta = 0.5 * (etaEdges[1:] + etaEdges[:-1])
    n = counts.sum(axis=1)

    if estimator == "fit":
        # the profile carries a zero width where the iterative fit did not
        # converge, which has to read as a gap rather than as a resolution
        sigma = np.where(width > 0, width, np.nan)
        return eta, sigma, np.where(width > 0, widthErr, np.nan), mean, n

    sigma = np.full(len(eta), np.nan)
    sigmaErr = np.full(len(eta), np.nan)
    median = np.full(len(eta), np.nan)
    for i, row in enumerate(counts):
        if n[i] < MIN_ENTRIES:
            continue
        # the cumulative distribution is known at the bin edges, so the
        # quantiles interpolate linearly inside a bin
        cum = np.concatenate([[0.0], np.cumsum(row)]) / n[i]
        lo, mid, hi = np.interp(QUANTILES, cum, resEdges)
        sigma[i] = 0.5 * (hi - lo)
        median[i] = mid
        sigmaErr[i] = sigma[i] / np.sqrt(2 * n[i])

    return eta, sigma, sigmaErr, median, n


def residualProjection(hist):
    """Residual distribution integrated over eta, as a density."""
    edges = hist[1]
    counts = hist[2].sum(axis=0)
    width = np.diff(edges)
    total = counts.sum()
    density = counts / width / total if total > 0 else counts
    return edges, density, total


def styleAxes(ax):
    ax.grid(True, which="major", color="#d8d8d4", linewidth=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#8a8a85")
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors="#52514e", labelsize=8)


def unitLabel(param, unit):
    return f"{param} [{unit}]" if unit else param


def resolutionPage(pdf, data, pt, variants, estimator):
    fig, axes = plt.subplots(2, len(PARAMS), figsize=(11, 6.5), sharex=True)
    fig.suptitle(
        f"Seed parameter performance at the perigee, "
        f"single muons, $p_\\mathrm{{T}} = {pt}$ GeV, ODD pixels",
        fontsize=12,
        y=0.98,
    )

    handles = []
    for col, (param, (label, unit)) in enumerate(PARAMS.items()):
        top, bottom = axes[0][col], axes[1][col]
        for variant in variants:
            hist = data.get((variant, pt, param))
            if hist is None:
                continue
            name, color, marker = VARIANTS[variant]
            eta, sigma, sigmaErr, median, _ = resolutionVsEta(hist, estimator)
            (line,) = top.plot(
                eta,
                sigma,
                color=color,
                marker=marker,
                markersize=3.5,
                linewidth=1.6,
                label=name,
            )
            top.fill_between(
                eta,
                sigma - sigmaErr,
                sigma + sigmaErr,
                color=color,
                alpha=0.18,
                linewidth=0,
            )
            bottom.plot(
                eta, median, color=color, marker=marker, markersize=3.5, linewidth=1.6
            )
            if col == 0:
                handles.append(line)

        biasName = "fitted mean" if estimator == "fit" else "median"
        top.set_yscale("log")
        top.set_title(label, fontsize=10, color="#0b0b0b")
        top.set_ylabel(f"resolution {unitLabel('', unit)}".strip(), fontsize=9)
        bottom.set_ylabel(
            f"bias ({biasName}) {unitLabel('', unit)}".strip(), fontsize=9
        )
        bottom.axhline(0.0, color="#8a8a85", linewidth=0.8, zorder=1)
        bottom.set_xlabel("$\\eta$", fontsize=10)
        styleAxes(top)
        styleAxes(bottom)

    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.005),
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    pdf.savefig(fig)
    plt.close(fig)


def distributionPage(pdf, data, pts, variants, estimator):
    fig, axes = plt.subplots(len(pts), len(PARAMS), figsize=(11, 3.1 * len(pts)))
    axes = np.atleast_2d(axes)
    fig.suptitle(
        "Residual distributions, integrated over $\\eta$", fontsize=12, y=0.99
    )

    handles = []
    for row, pt in enumerate(pts):
        for col, (param, (label, unit)) in enumerate(PARAMS.items()):
            ax = axes[row][col]
            for variant in variants:
                hist = data.get((variant, pt, param))
                if hist is None:
                    continue
                name, color, _ = VARIANTS[variant]
                edges, density, _ = residualProjection(hist)
                (line,) = ax.step(
                    edges[:-1], density, where="post", color=color, linewidth=1.4,
                    label=name,
                )
                if row == 0 and col == 0:
                    handles.append(line)

            # the axes reach far into the tails, so show the core
            ax.set_xlim(*coreRange(data, pt, param, variants, estimator))
            ax.set_yscale("log")
            ax.set_xlabel(unitLabel(label, unit), fontsize=9)
            if col == 0:
                ax.set_ylabel(
                    f"$p_\\mathrm{{T}} = {pt}$ GeV\ndensity", fontsize=9
                )
            styleAxes(ax)

    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.005),
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    pdf.savefig(fig)
    plt.close(fig)


def coreRange(data, pt, param, variants, estimator):
    """A window holding the core of the widest variant."""
    widest = 0.0
    for variant in variants:
        hist = data.get((variant, pt, param))
        if hist is None:
            continue
        _, sigma, _, _, _ = resolutionVsEta(hist, estimator)
        if np.any(np.isfinite(sigma)):
            widest = max(widest, np.nanmax(sigma))
    widest = widest or 1.0
    return -4 * widest, 4 * widest


def coveragePage(pdf, data, pts, variants):
    fig, axes = plt.subplots(1, len(pts), figsize=(11, 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    fig.suptitle(
        "Matched seeds per $\\eta$ bin - the population behind every point above",
        fontsize=11,
        y=0.99,
    )

    handles = []
    for col, pt in enumerate(pts):
        ax = axes[col]
        for variant in variants:
            hist = data.get((variant, pt, "d0"))
            if hist is None:
                continue
            name, color, marker = VARIANTS[variant]
            eta, _, _, _, n = resolutionVsEta(hist, "quantile")
            (line,) = ax.plot(
                eta, n, color=color, marker=marker, markersize=3.5, linewidth=1.6,
                label=name,
            )
            if col == 0:
                handles.append(line)
        ax.set_yscale("log")
        ax.set_title(f"$p_\\mathrm{{T}} = {pt}$ GeV", fontsize=10)
        ax.set_xlabel("$\\eta$", fontsize=10)
        if col == 0:
            ax.set_ylabel("matched seeds", fontsize=9)
        styleAxes(ax)

    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.01),
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    pdf.savefig(fig)
    plt.close(fig)


class PageSink:
    """A `PdfPages` that optionally drops a PNG of every page next to the PDF."""

    def __init__(self, pdf, pngPrefix=None):
        self._pdf = pdf
        self._pngPrefix = pngPrefix
        self._page = 0

    def savefig(self, fig):
        self._pdf.savefig(fig)
        if self._pngPrefix is not None:
            fig.savefig(f"{self._pngPrefix}_page{self._page}.png", dpi=140)
        self._page += 1


def load(inputDir):
    """Read every `res_<param>_vs_eta` into {(variant, pt, param): histogram}."""
    pattern = re.compile(r"performance_(?P<variant>.+)_pt(?P<pt>\d+)\.root$")
    data = {}
    pts = set()
    variants = []

    for path in sorted(inputDir.glob("performance_*.root")):
        match = pattern.match(path.name)
        if match is None or match["variant"] not in VARIANTS:
            continue
        variant, pt = match["variant"], int(match["pt"])
        with uproot.open(path) as handle:
            for param in PARAMS:
                key = f"res_{param}_vs_eta"
                if key not in handle:
                    continue
                hist = handle[key]
                width = handle[f"reswidth_{param}_vs_eta"]
                mean = handle[f"resmean_{param}_vs_eta"]
                data[(variant, pt, param)] = (
                    hist.axis(0).edges(),
                    hist.axis(1).edges(),
                    hist.values(),
                    width.values(),
                    width.errors(),
                    mean.values(),
                )
        pts.add(pt)
        if variant not in variants:
            variants.append(variant)

    variants.sort(key=lambda v: list(VARIANTS).index(v))
    return data, sorted(pts), variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputDir", help="Directory with the ROOT files", type=Path)
    parser.add_argument(
        "-o",
        "--output",
        help="Output PDF, defaults to seed_parameter_resolution.pdf next to the input",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--estimator",
        help="Resolution estimator, see the module docstring",
        choices=("fit", "quantile"),
        default="fit",
    )
    parser.add_argument(
        "--png", help="Also write a PNG per page", action="store_true"
    )
    args = parser.parse_args()

    data, pts, variants = load(args.inputDir)
    if not data:
        raise SystemExit(f"no performance files found in {args.inputDir}")

    if args.estimator == "fit":
        failed = sum(
            int(np.count_nonzero(hist[3] <= 0)) for hist in data.values()
        )
        if failed:
            print(f"{failed} eta bins without a converged Gaussian fit, left empty")

    output = args.output or args.inputDir / "seed_parameter_resolution.pdf"
    with PdfPages(output) as pdfFile:
        pdf = PageSink(pdfFile, str(output.with_suffix("")) if args.png else None)
        for pt in pts:
            resolutionPage(pdf, data, pt, variants, args.estimator)
        distributionPage(pdf, data, pts, variants, args.estimator)
        coveragePage(pdf, data, pts, variants)

    print(f"wrote {output}")


if __name__ == "__main__":
    main()
