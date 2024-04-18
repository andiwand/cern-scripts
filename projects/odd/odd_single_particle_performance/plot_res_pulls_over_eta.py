#!/usr/bin/env python3

import matplotlib.pyplot as plt
import uproot
import awkward as ak
import argparse
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("input", nargs="+")
args = parser.parse_args()

columns = [
    "pull_eLOC0_fit",
    "pull_eLOC1_fit",
    "pull_eT_fit",
    "pull_ePHI_fit",
    "pull_eTHETA_fit",
    "pull_eQOP_fit",
]
pull_range = (-8, 8)
std_range = (0, 4)

for f in args.input:
    tracksummary = uproot.open(f)
    tracksummary = ak.to_dataframe(
        tracksummary["tracksummary"].arrays(library="ak"),
        how="outer",
    )

    fig = plt.figure(f, figsize=(8, 6))
    subfigs = fig.subfigures(2, 3)

    for col, subfig in zip(
        columns,
        subfigs.flat,
    ):
        ax, ax_mean, ax_std = subfig.subplots(
            3,
            1,
            gridspec_kw={"height_ratios": [5, 1, 1], "hspace": 0},
            sharex=True,
        )

        data = tracksummary[col].dropna()

        ax.set_title(col)
        h, xedges, yedges, im = ax.hist2d(
            tracksummary["t_eta"],
            tracksummary[col],
            range=((-3, 3), pull_range),
            bins=50,
            density=True,
            cmap="Greys",
        )

        xmiddles = 0.5 * (xedges[:-1] + xedges[1:])
        ymiddles = 0.5 * (yedges[:-1] + yedges[1:])
        ydensity = h / np.sum(h, axis=1)

        ymean = np.sum(ymiddles * ydensity, axis=1)
        yvar = np.sum((ymiddles - ymean[:, np.newaxis]) ** 2 * ydensity, axis=1)
        ystd = np.sqrt(yvar)

        ax.plot(xmiddles, ymean, "r-", label="fit")
        ax.plot(xmiddles, ymean - ystd, "r--")
        ax.plot(xmiddles, ymean + ystd, "r--")

        ax_mean.plot(xmiddles, ymean, "r-")

        ax_std.plot(xmiddles, ystd, "r-")

        fig.colorbar(im, ax=subfig.get_axes())

plt.show()
