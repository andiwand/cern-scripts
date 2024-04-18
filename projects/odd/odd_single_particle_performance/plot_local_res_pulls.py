#!/usr/bin/env python3

import matplotlib.pyplot as plt
from scipy.stats import norm
import uproot
import awkward as ak
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("input", nargs="+")
args = parser.parse_args()

pulls = [
    "pull_eLOC0_fit",
    "pull_eLOC1_fit",
    "pull_eT_fit",
    "pull_ePHI_fit",
    "pull_eTHETA_fit",
    "pull_eQOP_fit",
]
residuals = [
    "res_eLOC0_fit",
    "res_eLOC1_fit",
    "res_eT_fit",
    "res_ePHI_fit",
    "res_eTHETA_fit",
    "res_eQOP_fit",
]

pull_range = (-8, 8)

for f in args.input:
    tracksummary = uproot.open(f)
    tracksummary = ak.to_dataframe(
        tracksummary["tracksummary"].arrays(library="ak"),
        how="outer",
    )

    fig = plt.figure(f"residuals {f}", figsize=(8, 6))
    axs = fig.subplots(2, 3)
    axs = [item for sublist in axs for item in sublist]

    for residual, ax in zip(
        residuals,
        axs,
    ):
        data = tracksummary[residual].dropna()
        mu, sigma = norm.fit(data)

        ax.set_title(residual)
        n, bins, patches = ax.hist(
            tracksummary[residual],
            bins=100,
            density=True,
            label=residual,
        )
        y = norm.pdf(bins, mu, sigma)
        ax.plot(bins, y, "r--", linewidth=2, label=f"mu={mu:.2f} sigma={sigma:.2f}")
        ax.legend()

    fig = plt.figure(f"pulls {f}", figsize=(8, 6))
    axs = fig.subplots(2, 3)
    axs = [item for sublist in axs for item in sublist]

    for pull, ax in zip(
        pulls,
        axs,
    ):
        data = tracksummary[pull].dropna()
        data = data[(data > pull_range[0]) & (data < pull_range[1])]
        mu, sigma = norm.fit(data)

        ax.set_title(pull)
        n, bins, patches = ax.hist(
            tracksummary[pull],
            bins=100,
            range=pull_range,
            density=True,
            label=pull,
        )
        y = norm.pdf(bins, mu, sigma)
        ax.plot(bins, y, "r--", linewidth=2, label=f"mu={mu:.2f} sigma={sigma:.2f}")
        ax.legend()

plt.show()
