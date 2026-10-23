#!/usr/bin/env python3
"""Plot staged ODD measurements and isolated physics references."""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--results", type=Path, required=True)
p.add_argument("--previous-results", type=Path, required=True)
a = p.parse_args()
r = a.results
old = a.previous_results
plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42})


def read(path):
    return json.loads(path.read_text())


def sem(x):
    return float(np.std(x, ddof=1) / np.sqrt(len(x)))


def values(rows, key="secondary"):
    return np.array([x[key] for x in rows])


stages = {
    name: read(path)["events"]
    for name, path in [
        ("Before this step", old / "full-ancestry.json"),
        ("Conversion", r / "conversion-ancestry.json"),
        ("+ neutral transport", r / "neutrals-ancestry.json"),
        ("+ prompt decays", r / "prompt-ancestry.json"),
        ("Geant4, ID only", old / "geant4-ancestry.json"),
    ]
}
summary = {"stages": {}, "paired_increments": {}}
for name, rows in stages.items():
    summary["stages"][name] = {
        "secondary_mean": float(values(rows).mean()),
        "secondary_sem": sem(values(rows)),
        "primary_mean": float(values(rows, "primary").mean()),
        "process_mean": {
            k: float(np.mean([x["process"][k] for x in rows]))
            for k in ["conversion", "decay", "nuclear"]
        },
    }
previous = "Before this step"
for name in ["Conversion", "+ neutral transport", "+ prompt decays"]:
    d = values(stages[name]) - values(stages[previous])
    summary["paired_increments"][name] = {"mean": float(d.mean()), "sem": sem(d)}
    previous = name
before = values(stages["Before this step"])
final = values(stages["+ prompt decays"])
g4 = values(stages["Geant4, ID only"])
summary["combined_gain"] = {
    "mean": float(np.mean(final - before)),
    "sem": sem(final - before),
}
summary["remaining_gap"] = {"mean": float(np.mean(g4 - final)), "sem": sem(g4 - final)}
summary["closed_previous_gap_fraction"] = float(
    np.mean(final - before) / np.mean(g4 - before)
)
(r / "refinement-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
page_number = 0
with PdfPages(r / "physics_refinements.pdf") as pdf:

    def save(fig, note=""):
        global page_number
        page_number += 1
        if note:
            fig.text(0.06, 0.025, note, fontsize=9, va="bottom")
        fig.tight_layout(rect=(0, 0.09, 1, 0.94))
        pdf.savefig(fig)
        fig.savefig(r / f"refinement_page{page_number}.png", dpi=110)
        plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Neutral transport and physics corrections — 20 matched ODD events")
    names = list(stages)
    x = np.arange(len(names))
    means = [summary["stages"][n]["secondary_mean"] for n in names]
    ax[0].bar(x, means, color=[".65", "#4c78a8", "#59a14f", "#f28e2b", ".3"])
    ax[0].errorbar(
        x,
        means,
        yerr=[summary["stages"][n]["secondary_sem"] for n in names],
        fmt="none",
        color="black",
        capsize=3,
    )
    ax[0].set_xticks(x, names, rotation=30, ha="right")
    ax[0].set_ylabel("Secondary pixel hits / event")
    ax[0].set_ylim(0, 21000)
    for i, y in enumerate(means):
        ax[0].text(i, y + 850, f"{y:,.0f}", ha="center")
    inc = summary["paired_increments"]
    ax[1].bar(
        range(3),
        [v["mean"] for v in inc.values()],
        color=["#4c78a8", "#59a14f", "#f28e2b"],
    )
    ax[1].errorbar(
        range(3),
        [v["mean"] for v in inc.values()],
        yerr=[v["sem"] for v in inc.values()],
        fmt="none",
        color="black",
        capsize=4,
    )
    ax[1].set_xticks(
        range(3),
        ["Conversion", "Neutral transport", "Prompt decays"],
        rotation=25,
        ha="right",
    )
    ax[1].set_ylabel("Incremental secondary hits / event")
    ax[1].axhline(0, color=".4", lw=0.8)
    save(
        fig,
        "Common hit-entry p ≥ 0.1 GeV, pT ≥ 0.05 GeV; pixel volumes 16–18. Error bars: event SEM.\nRight: paired differences. Changed RNG/cascades prevent adding isolated process contributions. Charged cuts unchanged.",
    )
    c = pd.read_csv(r / "conversion-reference.csv")
    fig, ax = plt.subplots(2, 2, figsize=(11.7, 8.3))
    fig.suptitle("Photon conversion: independent Bethe–Heitler reference in aluminium")
    for name, style in [("legacy", "--"), ("corrected", "-"), ("geant4-Al", ":")]:
        d = c[c.model == name]
        ax[0, 0].semilogx(d.energy_GeV, d.rate_per_X0, style, marker="o", label=name)
        ax[0, 1].loglog(
            d.energy_GeV, d.mean_electron_angle, style, marker="o", label=name
        )
        for col, energy in enumerate([0.01, 0.1]):
            q = d[np.isclose(d.energy_GeV, energy)].iloc[0]
            hist = q[[f"bin{i}" for i in range(50)]].to_numpy(dtype=float) / q.samples
            ax[1, col].plot((np.arange(50) + 0.5) / 50, hist, style, label=name)
            ax[1, col].set_title(f"Photon energy {energy*1000:g} MeV")
            ax[1, col].set_xlabel("Electron energy / photon energy")
            ax[1, col].set_ylabel("Probability / bin")
    ax[0, 0].set_ylabel("Conversion rate / X0")
    ax[0, 0].set_xlabel("Photon energy [GeV]")
    ax[0, 0].axhline(0, color=".7", lw=0.7)
    ax[0, 0].legend()
    ax[0, 1].set_ylabel("Mean electron angle [rad]")
    ax[0, 1].set_xlabel("Photon energy [GeV]")
    save(
        fig,
        "100,000 samples / energy / model. Fixed-Al rate approximation; default Fatras rate multiplier 0.98.\nLegacy negative low-energy rates and nonconserving daughter energies are retained here to expose the original failure.",
    )
    d = pd.read_csv(r / "decay-reference.csv")
    fig, axes = plt.subplots(2, 3, figsize=(11.7, 8.3))
    fig.suptitle("Native neutral decays: spectra and branching coverage")
    for ax, pdg in zip(axes.flat, [130, 221, 331, 113, 223]):
        for model in ["native", "geant4"]:
            q = d[(d.pdg == pdg) & (d.model == model)]
            n = q["count"].sum()
            assert n == 100000
            h = q[[f"bin{i}" for i in range(100)]].sum().to_numpy() / n
            ax.step((np.arange(100) + 0.5) * 0.005, h, where="mid", label=model)
        ax.set_title(f"PDG {pdg}")
        ax.set_xlabel("Charged-daughter rest-frame energy [GeV]")
        ax.set_ylabel("Daughters / decay / bin")
    axes[0, 0].legend()
    axes[1, 2].axis("off")
    axes[1, 2].text(
        0,
        0.95,
        "100,000 decays / species / model\n\nNative: PDG 2026 dominant channels\nUniform three-body phase space\nFixed resonance masses\n\nGeant4 11.3.2 decay tables\nDirect daughters, before cascades\n\nAgreement is not an exact spectrum fit.",
        va="top",
    )
    save(
        fig,
        "K-long three-body form factors, Dalitz slopes, resonance line shapes and rare leptonic modes are omitted.\nFinal ODD occupancy gain from the prompt modes is unresolved in this sample.",
    )
    h = pd.read_csv(r / "hadronic-reference.csv")
    fig, axes = plt.subplots(3, 2, figsize=(11.7, 8.3))
    fig.suptitle("Hadronic final states: target composition matters")
    for row, pdg in enumerate([211, -211, 2212]):
        for col, group in enumerate([0, 1]):
            ax = axes[row, col]
            for model in ["Fatras-Si", "Geant4-Si", "Geant4-C", "Geant4-Al"]:
                q = h[(h.projectile == pdg) & (h.group == group) & (h.model == model)]
                ax.errorbar(
                    q.p_GeV,
                    q.accepted_mean,
                    yerr=q.accepted_sem,
                    marker=".",
                    label=model,
                )
            ax.set_xscale("log")
            ax.set_title(
                f"Projectile {pdg}: " + ("charged pions" if group == 0 else "protons")
            )
            ax.set_ylabel("Accepted particles / interaction")
            ax.set_xlabel("Incident momentum [GeV/c]")
    axes[0, 0].legend(fontsize=8)
    save(
        fig,
        "Independent FTFP_BERT reference: 1,024 events / species / momentum / target; incident direction transverse to beam.\nSame p/pT cuts; ions retained in residual. Diagnostic samples reject 65 C, 0 Al, 1 Si invalid residuals; conditional spectra.\nA larger strict C export fails residual conservation. No carbon calibration or multiplicity tuning is enabled in transport.",
    )
