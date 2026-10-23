"""PDF comparison: all hits, regional gaps, photon spectra and kernel accuracy."""

import argparse
import csv
import json
from pathlib import Path
from statistics import median
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
r = json.loads((a.work / "analysis.json").read_text())
s = json.loads((a.work / "spectra.json").read_text())
cur = r["runs"]["current"]["mean"]
old = r["runs"]["Previous"]["mean"]
g4 = r["runs"]["Geant4"]["mean"]
plt.rcParams.update(
    {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
)
colors = ["#7d8791", "#007c91", "#b64d29"]
footer = "3 matched ttbar + fixed PU200 events; 2 T; physical ODD ID only. All written hits included. Geometry unchanged."
page = 0
with PdfPages(a.output) as pdf:

    def save(fig, bottom=0.06, caption=footer):
        global page
        page += 1
        fig.text(0.05, 0.025, caption, fontsize=8)
        fig.tight_layout(rect=[0.02, bottom, 0.99, 0.93])
        pdf.savefig(fig)
        if a.preview:
            fig.savefig(a.output.with_name(a.output.stem + f"-{page}.png"), dpi=120)
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13, 6))
    fig.suptitle("Inclusive hits and CPU: native radiation corrections", fontsize=17)
    labels = ["ACTS main\n300b664a3d", "Changed\nFatras", "Default\nGeant4"]
    for scope, ax in zip(["pixel", "ID"], axes):
        primary = [
            r["main"][scope + "_primary"],
            cur[scope + "_totals"]["primary"],
            g4[scope + "_totals"]["primary"],
        ]
        secondary = [
            r["main"][scope + "_secondary"],
            cur[scope + "_totals"]["secondary"],
            g4[scope + "_totals"]["secondary"],
        ]
        ax.bar(labels, primary, color=colors, alpha=0.3, label="Primary")
        ax.bar(labels, secondary, bottom=primary, color=colors, label="Secondary")
        for i, v in enumerate(secondary):
            ax.text(
                i, primary[i] + v + 1500, f"{v:,.0f} secondary", ha="center", fontsize=8
            )
        ax.set_title(scope + " hits / event")
        ax.set_ylim(0, max(np.array(primary) + secondary) * 1.2)
        ax.legend(fontsize=8)
    timing = [
        v["cpu_s_per_event"]
        for k, v in r["timings"].items()
        if k == "current" or k.startswith("current-repeat-")
    ]
    cpu = [
        r["archived_cpu"]["ACTS main"],
        median(timing),
        r["timings"]["geant4-refreshed"]["cpu_s_per_event"],
    ]
    axes[2].bar(labels, cpu, color=colors)
    axes[2].scatter([1] * len(timing), timing, color="black", s=20, zorder=3)
    for i, v in enumerate(cpu):
        axes[2].text(i, v + 0.7, f"{v:.2f}", ha="center")
    axes[2].set_title("CPU seconds / event")
    axes[2].set_ylim(0, max(cpu) * 1.2)
    axes[2].text(
        0.03,
        0.85,
        "Changed: median of 5 repeats\nMain: archived; G4: fresh run\nIncludes sequencer + CSV I/O",
        transform=axes[2].transAxes,
        fontsize=8,
    )
    save(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle("Where the secondary-hit gap remains", fontsize=17)
    groups = {
        "Pixel barrel": [17],
        "Pixel endcaps": [16, 18],
        "Strip barrels": [24, 29],
        "Strip endcaps": [23, 25, 28, 30],
    }
    x = np.arange(len(groups))
    width = 0.25
    for j, (name, data, col) in enumerate(
        [
            ("Compton-only control", old, colors[0]),
            ("Radiation corrected", cur, colors[1]),
            ("Geant4", g4, colors[2]),
        ]
    ):
        axes[0].bar(
            x + (j - 1) * width,
            [
                sum(data["ID_volume"].get(str(v), 0) for v in vols)
                for vols in groups.values()
            ],
            width,
            label=name,
            color=col,
        )
    axes[0].set_xticks(x, list(groups), rotation=20)
    axes[0].set_ylabel("Secondary hits / event")
    axes[0].legend(fontsize=8)
    processes = ["1", "2", "4", "5", "6"]
    x = np.arange(len(processes))
    for j, (name, data, col) in enumerate(
        [
            ("Compton-only control", old, colors[0]),
            ("Radiation corrected", cur, colors[1]),
            ("Geant4", g4, colors[2]),
        ]
    ):
        axes[1].bar(
            x + (j - 1) * width,
            [data["ID_process"].get(k, 0) for k in processes],
            width,
            color=col,
            label=name,
        )
    axes[1].set_xticks(
        x, ["Decay", "Pair conversion", "Nuclear", "Ionisation", "Other"], rotation=20
    )
    axes[1].set_ylabel("Secondary ID hits / event")
    axes[1].set_title("Carrier birth process; not causal attribution")
    save(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle("Interaction-model evidence", fontsize=17)
    labels = [
        "<0.1",
        "0.1–0.2",
        "0.2–1.022",
        "1.022–5",
        "5–20",
        "20–100",
        "100–1000",
        "≥1000",
    ]
    x = np.arange(8)
    for j, (name, label, col) in enumerate(
        [
            ("Previous", "Compton-only control", colors[0]),
            ("Coupled", "Radiation corrected", colors[1]),
            ("G4", "Geant4", colors[2]),
        ]
    ):
        axes[0].bar(
            x + (j - 1) * width,
            [s[name]["counts"].get("22/3/" + str(i), 0) for i in range(8)],
            width,
            color=col,
            label=label,
        )
    axes[0].set_xticks(x, labels, rotation=35)
    axes[0].set_yscale("log")
    axes[0].set_ylim(30, 1e5)
    axes[0].set_ylabel("Retained bremsstrahlung photons / event")
    axes[0].set_xlabel("Photon birth energy [MeV], including under/overflow")
    axes[0].legend(fontsize=8)
    axes[0].set_title("Photon supply feeding conversion and Compton")
    text = (
        "Physics changes\n\n"
        "• Photon energy cannot consume electron rest mass.\n"
        "• Explicit screened spectrum allows multiple photons.\n"
        "• Radiation is interleaved with ionisation before stopping.\n"
        "• Restricted soft radiation avoids double counting.\n\n"
        "No new runtime tables or G4 calls for this kernel.\n"
        "No extra navigation steps; material map unchanged.\n\n"
        "The hit gap is not solved. Changed random histories\n"
        "limit causal interpretation of the small inclusive gain.\n"
        "Production thresholds differ from default G4; this\n"
        "diagnostic spectrum is not a cut on the hit summary."
    )
    axes[1].axis("off")
    axes[1].text(0, 0.98, text, va="top", fontsize=11, linespacing=1.5)
    save(fig)
    data = list(csv.DictReader((a.work / "reference.csv").open()))
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle("Independent kernel validation against G4 Seltzer–Berger", fontsize=16)
    for ax, pdg in zip(axes, ["11", "-11"]):
        for material in ["G4_C", "G4_Si", "G4_Cu", "G4_Pb"]:
            selected = [
                v
                for v in data
                if v["material"] == material
                and v["pdg"] == pdg
                and float(v["cut_MeV"]) == 0.1
            ]
            ax.plot(
                [float(v["kinetic_MeV"]) for v in selected],
                [float(v["native_per_X0"]) / float(v["g4_per_X0"]) for v in selected],
                marker="o",
                label=material.removeprefix("G4_"),
            )
        ax.axhspan(0.9, 1.1, color="gray", alpha=0.15)
        ax.axhline(1, color="black", lw=0.7)
        ax.set_xscale("log")
        ax.set_ylim(0.2, 1.35)
        ax.set_xlabel("Incident kinetic energy [MeV]")
        ax.set_ylabel("Native / G4 rate above 100 keV")
        ax.legend()
        ax.set_title("Electrons" if pdg == "11" else "Positrons")
    fig.text(
        0.06,
        0.07,
        "Analytic effective-Z approximation: low-energy high-Z accuracy is limited. No detector tuning or G4 event changes.",
        fontsize=9,
    )
    save(
        fig,
        bottom=0.14,
        caption="Homogeneous-material rates; this comparison does not change the default G4 event simulation.",
    )
