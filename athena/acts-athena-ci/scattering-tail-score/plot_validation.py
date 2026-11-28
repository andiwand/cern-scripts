#!/usr/bin/env python3
"""Publication-friendly vector versions of the held-out comparison."""
import argparse
import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument("directory", type=Path)
p.add_argument("--input", default="validation.json")
p.add_argument("--prefix", default="")
p.add_argument("--calibration", default="Raw measurements")
a = p.parse_args()
d = json.loads((a.directory / a.input).read_text())
colors = ["#263b50", "#227c96", "#d35432"]
labels = [
    "No tail handling + quality cut",
    "Previous tail handling + quality cut",
    "Tail + normalized mixture score",
]
families = ["core", "previous", "new"]
plt.rcParams.update({"svg.fonttype": "none", "font.size": 10})
fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
for family, label, color in zip(families, labels, colors):
    points = []
    for retention, point in d["points"].items():
        if family not in point["groups"]:
            continue
        c = point["groups"][family]["validation"]
        points.append((100 * c["efficiency"], 100 * c["fake_rate"]))
    points.sort()
    ax.plot(*zip(*points), "o-", label=label, color=color, markersize=4)
ax.set(
    xlabel="Selected truth efficiency [%]",
    ylabel="Fake tracks / tracks [%]",
    title=f'Athena ITk · {a.calibration}\nExisting Geant4 ttbar μ=200 · {d["events"]} validation events',
)
ax.grid(alpha=0.2)
ax.legend(fontsize=8)
for ext in ["svg", "pdf"]:
    fig.savefig(a.directory / f"{a.prefix}tradeoff.{ext}")
plt.close(fig)
fig, axes = plt.subplots(1, 3, figsize=(10, 3.5), layout="constrained")
point = d["points"]["0.995"]
for ax, (field, label, scale) in zip(
    axes,
    [
        ("d0res", "d₀ [µm]", 1000),
        ("z0res", "z₀ [µm]", 1000),
        ("qptres", "Relative q/pT [%]", 100),
    ],
):
    for family, name, color in zip(families, labels, colors):
        r = point["groups"][family]["common_resolutions"][field]
        ax.plot(
            [68.27, 95],
            [scale * r["width68"], scale * r["width95"]],
            "o-",
            label=name,
            color=color,
            markersize=4,
        )
    ax.set(
        xlabel="Central interval [%]", ylabel="Half-width: " + label, xticks=[68.27, 95]
    )
    ax.grid(alpha=0.2)
axes[0].legend(fontsize=6.5)
fig.suptitle(
    f"Athena · {a.calibration}\nCommon prompt truth · frozen 99.5% training-retention point",
    fontsize=11,
)
for ext in ["svg", "pdf"]:
    fig.savefig(a.directory / f"{a.prefix}resolutions.{ext}")
plt.close(fig)
