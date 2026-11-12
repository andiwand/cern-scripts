#!/usr/bin/env python3
"""Tail fraction (beyond 3 sigma_main per |eta| x pT bin) vs |eta| for a few variants. usage: plottails.py resolsum.json out.png"""
import sys, json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
d = json.load(open(sys.argv[1])); E = d["etaEdges"]; x = [(E[i] + E[i + 1]) / 2 for i in range(len(E) - 1)]
S = [("main", "FML-T0-F (main)", "#2a78d6"), ("FML-T0-N", "FML-T0-N", "#eb6834"), ("FIT-T0-F", "FIT-T0-F", "#1baf7a"), ("trim-on-fit-ends", "FIT-T5-F", "#eda100")]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6", "axes.axisbelow": True})
fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.3))
for ax, (v, lab) in zip(axs, (("d0", "d0"), ("z0", "z0"), ("qpt", "q/pT"))):
    for n, l, c in S:
        y = [100 * t if t is not None else None for t in d["res"][n][v]["tailEta"]]
        ax.plot(x, y, marker="o", ms=4, lw=2, color=c, label=l)
    ax.set_title(f"{lab}: tail beyond 3σ of main", loc="left", fontsize=10); ax.set_xlabel("|η| of the particle"); ax.set_ylabel("% of matched tracks")
axs[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=130)
