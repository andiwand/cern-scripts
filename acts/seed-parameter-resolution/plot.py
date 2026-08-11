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

# markers with error bars and nothing joining them: neighbouring eta bins are
# independent measurements, and a line between them would suggest otherwise
MARKER_STYLE = dict(
    linestyle="none",
    markersize=3.5,
    elinewidth=0.9,
    capsize=0,
)


def resolutionVsEta(hist, estimator="fit"):
    """Resolution and bias with their errors per eta bin, plus the entry count.

    Returns eta, the half width of the eta bins, the resolution and its error,
    the bias and its error, and the number of entries.
    """
    etaEdges, resEdges, counts, width, widthErr, mean, meanErr = hist

    eta = 0.5 * (etaEdges[1:] + etaEdges[:-1])
    etaErr = 0.5 * np.diff(etaEdges)
    n = counts.sum(axis=1)

    if estimator == "fit":
        # the profile carries a zero width where the iterative fit did not
        # converge, which has to read as a gap rather than as a resolution
        converged = width > 0
        return (
            eta,
            etaErr,
            np.where(converged, width, np.nan),
            np.where(converged, widthErr, np.nan),
            np.where(converged, mean, np.nan),
            np.where(converged, meanErr, np.nan),
            n,
        )

    sigma = np.full(len(eta), np.nan)
    sigmaErr = np.full(len(eta), np.nan)
    median = np.full(len(eta), np.nan)
    medianErr = np.full(len(eta), np.nan)
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
        # the median of a Gaussian core is sqrt(pi/2) noisier than its mean
        medianErr[i] = 1.2533 * sigma[i] / np.sqrt(n[i])

    return eta, etaErr, sigma, sigmaErr, median, medianErr, n


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


def setRatioRange(ax, ratios):
    """Scale a ratio panel to its bulk and flag what runs off the top.

    The forward eta bins are an order of magnitude worse than the barrel, and
    letting them set the range leaves the barrel a flat line at one.
    """
    pooled = np.concatenate([r for _, r, _ in ratios]) if ratios else np.array([])
    pooled = pooled[np.isfinite(pooled)]
    if pooled.size == 0:
        return

    high = max(2.0, 1.15 * float(np.percentile(pooled, 80)))
    low = max(0.0, 0.9 * min(0.95, float(np.percentile(pooled, 5))))
    ax.set_ylim(low, high)

    for eta, ratio, color in ratios:
        offScale = np.isfinite(ratio) & (ratio > high)
        if np.any(offScale):
            ax.plot(
                eta[offScale],
                np.full(np.count_nonzero(offScale), high),
                marker="^",
                markersize=4,
                linestyle="none",
                color=color,
                clip_on=False,
                zorder=3,
            )


def resolutionPage(pdf, data, pt, variants, estimator, reference):
    fig, axes = plt.subplots(
        3,
        len(PARAMS),
        figsize=(13.5, 10.5),
        sharex=True,
        gridspec_kw=dict(height_ratios=[3.0, 1.6, 1.9]),
    )
    referenceName = VARIANTS[reference][0]
    fig.suptitle(
        f"Seed parameter performance at the perigee, "
        f"single muons, $p_\\mathrm{{T}} = {pt}$ GeV, ODD pixels",
        fontsize=13,
        y=0.985,
    )

    handles = []
    for col, (param, (label, unit)) in enumerate(PARAMS.items()):
        top, middle, bottom = axes[0][col], axes[1][col], axes[2][col]
        ratios = []

        referenceHist = data.get((reference, pt, param))
        referenceSigma = referenceSigmaErr = None
        if referenceHist is not None:
            _, _, referenceSigma, referenceSigmaErr, _, _, _ = resolutionVsEta(
                referenceHist, estimator
            )

        for variant in variants:
            hist = data.get((variant, pt, param))
            if hist is None:
                continue
            name, color, marker = VARIANTS[variant]
            eta, etaErr, sigma, sigmaErr, bias, biasErr, _ = resolutionVsEta(
                hist, estimator
            )
            point = top.errorbar(
                eta,
                sigma,
                yerr=sigmaErr,
                xerr=etaErr,
                color=color,
                marker=marker,
                label=name,
                **MARKER_STYLE,
            )
            bottom.errorbar(
                eta,
                bias,
                yerr=biasErr,
                xerr=etaErr,
                color=color,
                marker=marker,
                **MARKER_STYLE,
            )

            if referenceSigma is not None and variant != reference:
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = sigma / referenceSigma
                    # the variants run over the same muons, so the fluctuations
                    # partly cancel and adding the errors in quadrature is
                    # conservative
                    ratioErr = ratio * np.hypot(
                        sigmaErr / sigma, referenceSigmaErr / referenceSigma
                    )
                middle.errorbar(
                    eta,
                    ratio,
                    yerr=ratioErr,
                    xerr=etaErr,
                    color=color,
                    marker=marker,
                    **MARKER_STYLE,
                )
                ratios.append((eta, ratio, color))
            if col == 0:
                handles.append(point)

        setRatioRange(middle, ratios)

        if referenceSigma is not None:
            # the reference sits at one by construction; its own error is the
            # band every point above is measured against
            relative = np.nan_to_num(referenceSigmaErr / referenceSigma)
            etaRef, etaRefErr = resolutionVsEta(referenceHist, estimator)[:2]
            middle.bar(
                etaRef,
                height=2 * relative,
                bottom=1 - relative,
                width=2 * etaRefErr,
                color=VARIANTS[reference][1],
                alpha=0.25,
                linewidth=0,
                zorder=1,
            )

        biasName = "fitted mean" if estimator == "fit" else "median"
        top.set_yscale("log")
        top.set_title(label, fontsize=11, color="#0b0b0b")
        top.set_ylabel(f"resolution {unitLabel('', unit)}".strip(), fontsize=9)
        middle.set_ylabel(f"ratio to\n{referenceName}", fontsize=9)
        middle.axhline(1.0, color="#8a8a85", linewidth=0.8, zorder=2)
        bottom.set_ylabel(
            f"bias ({biasName}) {unitLabel('', unit)}".strip(), fontsize=9
        )
        bottom.axhline(0.0, color="#8a8a85", linewidth=0.8, zorder=1)
        bottom.set_xlabel("$\\eta$", fontsize=11)
        for ax in (top, middle, bottom):
            styleAxes(ax)

    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=10,
        bbox_to_anchor=(0.5, -0.004),
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
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
        _, _, sigma, _, _, _, _ = resolutionVsEta(hist, estimator)
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
            eta, etaErr, _, _, _, _, n = resolutionVsEta(hist, "quantile")
            point = ax.errorbar(
                eta,
                n,
                yerr=np.sqrt(n),
                xerr=etaErr,
                color=color,
                marker=marker,
                label=name,
                **MARKER_STYLE,
            )
            if col == 0:
                handles.append(point)
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
                    mean.errors(),
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
        "--reference",
        help="Variant the ratio panels divide by",
        choices=list(VARIANTS),
        default="truth_all",
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
            resolutionPage(pdf, data, pt, variants, args.estimator, args.reference)
        distributionPage(pdf, data, pts, variants, args.estimator)
        coveragePage(pdf, data, pts, variants)

    print(f"wrote {output}")


if __name__ == "__main__":
    main()
