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
parser.add_argument("finding_perf", type=Path)
parser.add_argument("x", choices=["eta", "d0", "z0", "pt", "lowpt", "prodr"], help="Variable to plot against")
parser.add_argument(
    "--output",
    type=Path,
    help="Path to output file",
)
parser.add_argument("--show", action="store_true", help="Show plot")
args = parser.parse_args()

xlabel = {
    "eta": r"true $\eta$",
    "d0": r"true $d_0$ [mm]",
    "z0": r"true $z_0$ [mm]",
    "pt": r"true $p_{T}$ [GeV]",
    "lowpt": r"true $p_{T}$ [GeV]",
    "prodr": r"true production radius [mm]",
}[args.x]
xrange = {
    "eta": (-3, 3),
    "d0": (-100, 100),
    "z0": (-100, 100),
    "pt": (0, 40),
    "lowpt": (0.5, 2),
    "prodr": (0, 24),
}[args.x]
histname = {
    "eta": "trackeff_vs_eta",
    "d0": "trackeff_vs_d0",
    "z0": "trackeff_vs_z0",
    "pt": "trackeff_vs_pT",
    "lowpt": "trackeff_vs_LowPt",
    "prodr": "trackeff_vs_prodR",
}[args.x]

pu = [200]
finding_perf = [
    args.finding_perf,
]
finding_perf = [ROOT.TFile.Open(p.absolute().as_posix()) for p in finding_perf]

fig, ax = plt.subplots(1, 1, figsize=(8, 4))

ax.set_xlabel(xlabel)
ax.set_ylabel("Technical efficiency")

ax.set_xlim(*xrange)

ax.hlines(1, *xrange, linestyles="--", color="gray")

for i, p, perf in zip(range(3), pu, finding_perf):
    eff = TH1(perf.Get(histname), xrange=xrange)
    label = f"<$\\mu$> = {p}" if len(pu) > 1 else None
    eff.errorbar(
        ax, label=label, marker=get_marker(i), linestyle="", color=get_color(i)
    )

ax.legend()

subtext = "ACTS v44.0.1\n$t\\bar{t}$, $\\sqrt{s}$ = 14 TeV"
if len(pu) == 1:
    subtext += f", <$\\mu$> = {pu[0]}"

atlasify.atlasify(
    axes=ax,
    brand="ODD",
    atlas="Simulation",
    subtext=subtext,
    enlarge=1.4,
)

fig.tight_layout()

if args.output is not None:
    fig.savefig(args.output)

if args.output is None or args.show:
    plt.show()
