"""Inclusive PDF comparison; diagnostic partitions do not discard hits."""

import argparse
import csv
import json
from pathlib import Path
import statistics
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--preview", action="store_true")
a = p.parse_args()
x = json.loads((a.work / "analysis.json").read_text())
runs = x["runs"]
main = x["main"]
new = runs["compton-100"]["mean"]
control = runs["Control"]["mean"]
g4 = runs["Geant4"]["mean"]
colors = ["#777777", "#cc9955", "#2579ad", "#203a32"]
plt.rcParams.update(
    {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
)
notes = "3 identical ttbar + fixed PU200 events, 2 T, physical ODD ID; all written hits, no analysis cuts."
a.output.parent.mkdir(parents=True, exist_ok=True)


def finish(pdf, fig, title, footer=notes):
    fig.suptitle(title, fontsize=15)
    fig.text(0.04, 0.025, footer, fontsize=8)
    fig.tight_layout(rect=[0, 0.07, 1, 0.95])
    pdf.savefig(fig)
    if a.preview:
        fig.savefig(a.output.with_name(f"preview-{pdf.get_pagecount()}.png"), dpi=120)
    plt.close(fig)


def bar_groups(ax, labels, series):
    pos = np.arange(len(labels))
    width = 0.8 / len(series)
    for i, (name, values, color) in enumerate(series):
        ax.bar(pos - 0.4 + (i + 0.5) * width, values, width, label=name, color=color)
    ax.set_xticks(pos, labels)
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)


with PdfPages(a.output) as pdf:
    fig, axes = plt.subplots(1, 3, figsize=(13, 5))
    names = [
        "ACTS main\n300b664a3d",
        "Fatras\nCompton\noff",
        "Fatras\nCompton\non",
        "Geant4\nID only",
    ]
    for ax, region in zip(axes[:2], ["pixel", "ID"]):
        primary = [
            main[region + "_primary"],
            control[region + "_totals"]["primary"],
            new[region + "_totals"]["primary"],
            g4[region + "_totals"]["primary"],
        ]
        secondary = [
            main[region + "_secondary"],
            control[region + "_totals"]["secondary"],
            new[region + "_totals"]["secondary"],
            g4[region + "_totals"]["secondary"],
        ]
        ax.bar(names, primary, color=colors, alpha=0.35, label="Primary")
        ax.bar(names, secondary, bottom=primary, color=colors, label="Secondary")
        for i, (first, second) in enumerate(zip(primary, secondary)):
            ax.text(
                i,
                first + second,
                f"{second:,.0f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        ax.set_ylim(0, max(np.array(primary) + secondary) * 1.13)
        ax.set_title(region + " hits / event")
        ax.set_ylabel("All hits (labels: secondary contribution)")
        ax.legend(fontsize=8)
    timings = x["timings"]
    current = [
        v["cpu_s_per_event"]
        for k, v in timings.items()
        if k == "compton-100" or k.startswith("repeat-compton")
    ]
    controls = [
        v["cpu_s_per_event"]
        for k, v in timings.items()
        if k == "disabled-check" or k.startswith("repeat-control")
    ]
    cpu = [
        x["archived_cpu"]["ACTS main"],
        statistics.median(controls),
        statistics.median(current),
        x["archived_cpu"]["Geant4"],
    ]
    axes[2].bar(names, cpu, color=colors)
    for i, value in enumerate(cpu):
        axes[2].text(i, value, f"{value:.2f}", ha="center", va="bottom")
    axes[2].set_ylim(0, max(cpu) * 1.15)
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8)
    axes[2].set_title("CPU seconds / event")
    axes[2].set_ylabel("Sequencer process user + system time")
    finish(
        pdf,
        fig,
        "Native Compton: inclusive hits and CPU",
        notes
        + "\nMain CPU: archived 5 events; G4 CPU: archived 3. Changed Fatras/control: median sequential repeats. No geometry changes.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    regions = {
        "Pixel barrel": [17],
        "Pixel endcaps": [16, 18],
        "Strip barrels": [24, 29],
        "Strip endcaps": [23, 25, 28, 30],
    }
    series = []
    for label, data, col in [
        ("Fatras Compton off", control, colors[1]),
        ("Fatras Compton on", new, colors[2]),
        ("Geant4", g4, colors[3]),
    ]:
        series.append(
            (
                label,
                [
                    sum(data["ID_volume"].get(str(v), 0) for v in volumes)
                    for volumes in regions.values()
                ],
                col,
            )
        )
    bar_groups(axes[0], list(regions), series)
    axes[0].set_title("Secondary hits by region")
    axes[0].set_ylabel("Hits / event")
    axes[0].tick_params(axis="x", rotation=15)
    processes = {
        "Decay": "1",
        "Pair": "2",
        "Nuclear": "4",
        "Ionisation": "5",
        "Other": "6",
    }
    bar_groups(
        axes[1],
        list(processes),
        [
            (label, [data["ID_process"].get(v, 0) for v in processes.values()], col)
            for label, data, col in [
                ("Fatras Compton off", control, colors[1]),
                ("Fatras Compton on", new, colors[2]),
                ("Geant4", g4, colors[3]),
            ]
        ],
    )
    axes[1].set_title("Carrier birth process, all ID")
    axes[1].legend(fontsize=8)
    finish(
        pdf,
        fig,
        "Where the secondary hits change",
        notes
        + "\nOther: native Compton; G4 additionally includes photoelectric and smaller channels. Process contributions are not causal net gains.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(13, 5))
    available = [
        name
        for name in ["compton-50", "compton-100", "compton-200", "compton-pair-cut"]
        if name in runs
    ]
    labels = [
        f'{runs[name]["metadata"]["soft_physics"]["photon_cut_GeV"]*1000:g}'
        for name in available
    ]
    for ax, region in zip(axes[:2], ["pixel", "ID"]):
        values = [
            runs[name]["mean"][region + "_totals"]["secondary"] for name in available
        ]
        ax.bar(labels, values, color=colors[2])
        ax.axhline(g4[region + "_totals"]["secondary"], color=colors[3], label="G4")
        ax.set_title(region + " secondary hits / event")
        ax.set_xlabel("Photon threshold [MeV]")
        ax.legend()
    values = [timings[name]["cpu_s_per_event"] for name in available]
    axes[2].bar(labels, values, color=colors[2])
    axes[2].set_title("CPU seconds / event (single runs)")
    axes[2].set_xlabel("Photon threshold [MeV]")
    finish(
        pdf,
        fig,
        "Photon-threshold sensitivity",
        notes
        + "\nCharged p >= 0.2 MeV, pT >= 0.05 MeV; 4 turns / 50000 steps retained. Random histories change between thresholds.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    with (a.work / "reference.csv").open() as f:
        rows = list(csv.DictReader(f))
    for z, label in [(6, "Carbon"), (14, "Silicon"), (29, "Copper"), (82, "Lead")]:
        rr = [row for row in rows if float(row["Z"]) == z]
        energies = [float(row["energy_MeV"]) for row in rr]
        ratio = [float(row["native_barn"]) / float(row["g4_barn"]) - 1 for row in rr]
        axes[0].semilogx(energies, 100 * np.array(ratio), marker=".", label=label)
    axes[0].axhline(0, color="black", lw=0.7)
    axes[0].axvline(0.1, color="grey", ls="--")
    axes[0].set_xlabel("Photon energy [MeV]")
    axes[0].set_ylabel("Native / G4 cross section - 1 [%]")
    axes[0].legend()
    axes[0].set_title("Free-electron approximation versus G4")
    axes[1].axis("off")
    text = "Native model and checks\n\n• No new data files or G4 runtime/thread dependency.\n• Geometry supplies local electron density.\n• Energy/momentum conservation and KN spectrum checked.\n• Exponential survival and conversion competition checked.\n• Shared immutable model: independent worker replay.\n\nRemaining limitations\n\n• No atomic binding, Doppler broadening or photoelectric effect.\n• At most one interaction per surface slab.\n• No propagation through the remainder of the birth slab.\n• No sensor-local material or extra birth hits added.\n• Bounded-navigation validation remains single-worker."
    axes[1].text(0.02, 0.98, text, va="top", fontsize=11, linespacing=1.5)
    finish(
        pdf,
        fig,
        "Accuracy limits and implementation scope",
        "G4 11.3.2 KleinNishinaModel cross sections; element scan is validation output, not runtime model input.",
    )
print(a.output)
