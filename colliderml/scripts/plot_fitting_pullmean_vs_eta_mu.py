#!/usr/bin/env python3

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import ROOT
import atlasify

from mycommon1.root import TH1
from mycommon1.plots import get_color, get_marker


base_dir = Path(__file__).parent.parent.parent

parser = argparse.ArgumentParser()
parser.add_argument("mu1GeV_fitting_perf", type=Path)
parser.add_argument("mu10GeV_fitting_perf", type=Path)
parser.add_argument("mu100GeV_fitting_perf", type=Path)
parser.add_argument(
    "--output",
    type=Path,
    help="Path to output file",
)
parser.add_argument("--show", action="store_true", help="Show plot")
args = parser.parse_args()

pts = [1, 10, 100]
fitting_perf = [
    args.mu1GeV_fitting_perf,
    args.mu10GeV_fitting_perf,
    args.mu100GeV_fitting_perf,
]
fitting_perf = [ROOT.TFile.Open(p.absolute().as_posix()) for p in fitting_perf]

params = ["d0", "z0", "phi", "theta", "qop", "t"]
ylabels = ["$d_0$", "$z_0$", r"$\phi$", r"$\theta$", "$q/p$", "$t$"]

fig, axs = plt.subplots(6, 1, figsize=(8, 6), sharex=True)

for i, ax, param, ylabel in zip(range(6), axs, params, ylabels):
    ax.hlines(0, -3, 3, linestyles="--", color="gray")

    ax.set_xlim(-3, 3)

    if i == 5:
        ax.set_xlabel(r"true $\eta$")
    ax.set_ylabel(ylabel)

    for j, pt, perf in zip(range(3), pts, fitting_perf):
        pull_mean = TH1(perf.Get(f"pullmean_{param}_vs_eta"), xrange=(-3, 3))

        pull_mean.errorbar(
            ax,
            label=f"{pt} GeV",
            marker=get_marker(j),
            linestyle="",
            color=get_color(j),
        )

    low, high = ax.get_ylim()
    bound = max(abs(low), abs(high))
    ax.set_ylim(-bound, bound)

    if i == 0:
        ax.legend(bbox_to_anchor=(1.0, 2.4), loc="upper right")

        atlasify.atlasify(
            axes=ax,
            outside=True,
            brand="ODD",
            atlas="Simulation",
            subtext="ACTS v40.0.0\nsingle muons, <$\\mu$> = 0",
            offset=18,
        )
    else:
        atlasify.atlasify(axes=ax, outside=True, atlas=False, offset=0)
        ax.get_legend().remove()

fig.tight_layout(h_pad=-0.01)

if args.output is not None:
    fig.savefig(args.output)

if args.output is None or args.show:
    plt.show()
