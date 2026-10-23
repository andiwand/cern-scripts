"""Uncut inclusive comparison, regional/process diagnostics and slab response."""

import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--preview", action="store_true")
a = p.parse_args()
d = json.loads((a.work / "analysis.json").read_text())
plt.rcParams.update(
    {
        "font.size": 11,
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
colors = ["#888888", "#2278b5", "#df7d20"]
cur = d["runs"]["Current"]["mean"]
before = d["runs"]["Before"]["mean"]
g4 = d["runs"]["Geant4"]["mean"]
page = 0
with PdfPages(a.output) as pdf:

    def save(
        fig,
        title,
        note,
        footer="Three ttbar + fixed PU200 events · all written ID hits · unchanged geometry · default G4 confined to ODD ID",
    ):
        global page
        page += 1
        fig.suptitle(title, fontsize=19, y=0.97)
        fig.subplots_adjust(left=0.075, right=0.975, top=0.81, bottom=0.25, wspace=0.35)
        fig.text(0.075, 0.14, note, fontsize=11, va="top")
        fig.text(0.03, 0.025, footer, fontsize=9)
        pdf.savefig(fig)
        if a.preview:
            fig.savefig(a.output.with_name(a.output.stem + f"-{page}.png"), dpi=120)
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 8))
    labels = ["ACTS main", "Changed Fatras", "Geant4"]
    for ax, scope in zip(axes[:2], ["pixel", "ID"]):
        pri = [
            d["main"][scope + "_primary"],
            cur[scope + "_totals"]["primary"],
            g4[scope + "_totals"]["primary"],
        ]
        sec = [
            d["main"][scope + "_secondary"],
            cur[scope + "_totals"]["secondary"],
            g4[scope + "_totals"]["secondary"],
        ]
        ax.bar(labels, np.array(pri) / 1000, color=colors, alpha=0.3, label="Primary")
        ax.bar(
            labels,
            np.array(sec) / 1000,
            bottom=np.array(pri) / 1000,
            color=colors,
            label="Secondary",
        )
        for i, n in enumerate(sec):
            ax.text(i, (pri[i] + n) / 1000 + 2, f"{n:,.0f}", ha="center", fontsize=10)
        ax.set_ylim(0, max(np.array(pri) + sec) / 1000 * 1.15)
        ax.set_ylabel("Thousands of hits / event")
        ax.set_title(
            f"{("Pixel" if scope == "pixel" else "ID")} hits\n(labels: secondary counts)"
        )
        ax.tick_params(axis="x", rotation=15)
    axes[0].legend(fontsize=9)
    cpu = [
        d["timings"]["main_archived"],
        d["timings"]["current"]["median"],
        d["timings"]["geant4_archived"],
    ]
    axes[2].bar(labels, cpu, color=colors)
    axes[2].scatter(
        [1] * 3, d["timings"]["current"]["samples"], color="black", s=25, zorder=5
    )
    for i, n in enumerate(cpu):
        axes[2].text(i, n + 0.6, f"{n:.2f}", ha="center")
    axes[2].set_title("CPU seconds / event")
    axes[2].tick_params(axis="x", rotation=15)
    gap = lambda m, s: 100 * (
        1 - m[s + "_totals"]["secondary"] / g4[s + "_totals"]["secondary"]
    )
    save(
        fig,
        "Photon birth-column transport: inclusive hits and CPU",
        f'Secondary ID deficit: {gap(before,"ID"):.2f}% → {gap(cur,"ID"):.2f}%; pixel deficit: {gap(before,"pixel"):.2f}% → {gap(cur,"pixel"):.2f}%.\n'
        f'Matched CPU medians: Fatras 5825d58880 {d["timings"]["control"]["median"]:.2f} s; changed {cpu[1]:.2f} s (three serial repeats each).\n'
        "ACTS main is pinned to 300b664a3d. Main CPU: archived five-event run; G4 CPU: archived same-day three-event run.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    regions = {
        "Pixel barrel": [17],
        "Pixel endcaps": [16, 18],
        "Strip barrels": [24, 29],
        "Strip endcaps": [23, 25, 28, 30],
    }
    for i, (name, m) in enumerate([("Changed Fatras", cur), ("Geant4", g4)]):
        axes[0].bar(
            np.arange(4) + (i - 0.5) * 0.35,
            [
                sum(m["ID_volume"].get(str(v), 0) for v in ids) / 1000
                for ids in regions.values()
            ],
            width=0.35,
            color=colors[i + 1],
            label=name,
        )
        axes[1].bar(
            np.arange(5) + (i - 0.5) * 0.35,
            [m["ID_process"].get(k, 0) / 1000 for k in ["1", "2", "4", "5", "6"]],
            width=0.35,
            color=colors[i + 1],
            label=name,
        )
    axes[0].set_xticks(range(4), regions, rotation=15)
    axes[1].set_xticks(
        range(5), ["Decay", "Conversion", "Nuclear", "Ionisation", "Other"], rotation=15
    )
    axes[0].set_title("Secondary hits by detector region")
    axes[1].set_title("Secondary hits by carrier birth process")
    for ax in axes:
        ax.set_ylabel("Thousands / event")
        ax.legend(fontsize=9)
    save(
        fig,
        "Remaining spatial and process differences",
        "Birth-process labels describe the hit carrier; they are not additive causal contributions to the deficit.\n"
        "The material map and sensor material placement are unchanged. Recoil-electron and ionisation-daughter birth columns remain deferred.\n"
        "No cross-section multiplier, occupancy correction or noise-hit injection is applied.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 8))
    cases = [
        ("primary-common-G4_Si-22-1-30", "compton", "1 MeV photon: Compton recoils"),
        (
            "cascade-common-G4_Si-11-20-30",
            "compton",
            "20 MeV electron: Compton recoils",
        ),
        (
            "cascade-common-G4_Si-11-20-30",
            "escape_charged",
            "20 MeV electron: charged escape",
        ),
    ]
    for ax, (prefix, metric, title) in zip(axes, cases):
        one = d["slabs"][prefix + "-fatras-1"]
        fine = d["slabs"][prefix + "-fatras-1000"]
        vals = [
            one["Before"][metric],
            one["Current"][metric],
            fine["Current"][metric],
            one["Geant4"][metric],
        ]
        names = ["5825\n1 slab", "Changed\n1 slab", "Changed\n1000 slices", "G4"]
        for i, v in enumerate(vals):
            ax.bar(
                i,
                v["mean"],
                yerr=v["sem"],
                color=["#888", "#2278b5", "#39a05d", "#df7d20"][i],
                capsize=3,
            )
            ax.text(
                i,
                v["mean"] + max(x["mean"] for x in vals) * 0.04,
                f'{v["mean"]:.3f}',
                ha="center",
                fontsize=10,
            )
        ax.set_xticks(range(4), names, fontsize=9)
        ax.set_title(title)
        ax.set_ylabel("Mean count / incident particle")
        ax.set_ylim(0, max(v["mean"] for v in vals) * 1.22)
    save(
        fig,
        "Same-material slabs: photon omission fixed; charged escape remains",
        "30 mm silicon; 100,000 primaries per setting; errors are event-level standard errors. Common EM processes; scattering off.\n"
        "Photon continuation restores repeated Compton interactions and interactions of brems photons within their birth column.\n"
        "Recoil/ionisation daughters still skip birth material. Fine slicing is not the production solution, especially with scattering enabled.",
        footer="Matched G4 NIST material and 100 keV production cuts · diagnostic thresholds only · no cuts on the inclusive plots",
    )
