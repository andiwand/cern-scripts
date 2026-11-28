#!/usr/bin/env python3
"""Plot ODD efficiency/fake tradeoffs from analyze.py summaries."""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument("directory", type=Path)
a = p.parse_args()
fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained", sharey=True)
for ax, pu in zip(axes, [200, 400]):
    summary = json.loads((a.directory / f"pu{pu}/summary.json").read_text())
    variants = summary["variants"]
    for name, color in [("core25", "tab:gray"), ("tail", "tab:blue")]:
        scan = variants[name + "_ambi"]["scan"]
        points = [(int(c), m) for c, m in scan.items() if int(c) >= 40]
        ax.plot(
            [100 * m["efficiency"] for _, m in points],
            [100 * m["fake_fraction"] for _, m in points],
            ".-",
            color=color,
            label=f"{name}: offline T cut",
        )
        if name == "tail":
            for c, m in points:
                if c in [40, 60, 80]:
                    ax.annotate(
                        str(c),
                        (100 * m["efficiency"], 100 * m["fake_fraction"]),
                        xytext=(3, 3),
                        textcoords="offset points",
                        fontsize=8,
                    )
    fit_scan = variants["tail_ambi"]["fit_chi2_scan"]
    points = [m for c, m in fit_scan.items() if int(c) >= 40]
    ax.plot(
        [100 * m["efficiency"] for m in points],
        [100 * m["fake_fraction"] for m in points],
        ".--",
        color="tab:purple",
        label="tail: offline fit chi2 cut",
    )
    for name, marker, color in [
        ("core15", "s", "black"),
        ("core25", "s", "tab:gray"),
        ("core49", "s", "tab:orange"),
        ("tail", "o", "tab:blue"),
        ("tail80", "*", "tab:red"),
    ]:
        m = variants[name + "_ambi"]
        ax.scatter(
            100 * m["efficiency"],
            100 * m["fake_fraction"],
            marker=marker,
            color=color,
            s=50,
            zorder=3,
            label="tail: live T ≤ 80" if name == "tail80" else name,
        )
    ax.set_title(f"ODD, pileup {pu}, {summary['events']} events")
    ax.set_xlabel("Selected truth-particle efficiency [%]")
    ax.grid(alpha=0.2)
axes[0].set_ylabel("Fake tracks / all tracks [%]")
axes[1].legend(fontsize=8, loc="upper left")
fig.suptitle("Fatras GeneralMixture; after greedy ambiguity resolution", fontsize=11)
for suffix in ["png", "pdf"]:
    fig.savefig(a.directory / f"tradeoff.{suffix}", dpi=180)
