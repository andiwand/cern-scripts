#!/usr/bin/env python3
"""Uncut final-state validation at fixed incident momenta (not a transport test)."""

import argparse, csv, json, collections
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def open_csv(path):
    import gzip

    return (
        path.open() if path.exists() else gzip.open(path.with_suffix(".csv.gz"), "rt")
    )


p = argparse.ArgumentParser()
p.add_argument("results", type=Path)
a = p.parse_args()
with open_csv(a.results / "events.csv") as f:
    events = list(csv.DictReader(f))
with open_csv(a.results / "rates.csv") as f:
    rates = list(csv.DictReader(f))
channels = [211, -211, 2212, 2112, 130, -2212, -2112, 321, -321]
names = ["π+", "π−", "p", "n", "KL", "anti-p", "anti-n", "K+", "K−"]
colors = ["#279b6c", "#4c78a8"]
models = ["On-demand FTFP_BERT", "Event replay"]
groups = collections.defaultdict(list)
for e in events:
    groups[int(e["model"]), int(e["pdg"]), float(e["p"])].append(e)
plt.rcParams.update({"pdf.fonttype": 42, "font.size": 9})
with PdfPages(a.results / "final_states.pdf") as pdf:
    for key, title in [
        ("multiplicity", "All emitted particles / interaction"),
        ("charged", "Charged particles / interaction"),
        ("leading_fraction", "Leading-particle energy / incident-particle energy"),
    ]:
        fig, axs = plt.subplots(3, 3, figsize=(11.7, 8.3))
        fig.suptitle(title)
        for ax, pdg, name in zip(axs.flat, channels, names):
            for mode in [0, 1]:
                momenta = sorted(p for m, c, p in groups if m == mode and c == pdg)
                means = []
                errs = []
                for q in momenta:
                    values = np.array([float(e[key]) for e in groups[mode, pdg, q]])
                    means.append(values.mean())
                    errs.append(values.std(ddof=1) / np.sqrt(len(values)))
                ax.errorbar(
                    momenta,
                    means,
                    yerr=errs,
                    marker=".",
                    color=colors[mode],
                    label=models[mode],
                    capsize=2,
                )
            ax.set_xscale("log")
            ax.set_title(name)
            ax.set_xlabel("Incident p [GeV/c]")
        axs.flat[0].legend(fontsize=8)
        fig.text(
            0.04,
            0.025,
            "512 seeded on-demand events per point; replay uses up to 512 distinct stored events per node. Error bars: sample SEM.\nNo daughter cuts. Target fragments remain in the residual. Leading energy can include energy released from the target.",
            fontsize=8,
        )
        fig.tight_layout(rect=(0, 0.1, 1, 0.95))
        pdf.savefig(fig)
        plt.close(fig)
    fig, axs = plt.subplots(3, 3, figsize=(11.7, 8.3))
    fig.suptitle("Interaction rates relative to the reference nuclear length")
    for ax, pdg, name in zip(axs.flat, channels, names):
        rows = sorted(
            [e for e in rates if int(e["pdg"]) == pdg], key=lambda e: float(e["p"])
        )
        for mode, key in enumerate(["live", "table"]):
            ax.plot(
                [float(e["p"]) for e in rows],
                [float(e[key]) for e in rows],
                marker=".",
                color=colors[mode],
                label=models[mode],
            )
        ax.set_xscale("log")
        ax.set_title(name)
        ax.set_xlabel("Incident p [GeV/c]")
        ax.set_ylabel("Rate / L0")
    axs.flat[0].legend(fontsize=8)
    fig.text(
        0.04,
        0.025,
        "Silicon reference in both models. Replay is zero outside its grid. On-demand rates use the physics list directly.\nBoth multiply the transported slab’s local thickness/L0; this is not a calibration of arbitrary material mixtures.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    pdf.savefig(fig)
    plt.close(fig)

    # Marginal daughter spectra at a common momentum. No daughter momentum cuts.
    spectra = collections.defaultdict(list)
    angles = collections.defaultdict(list)
    zero_momentum = 0
    with open_csv(a.results / "products.csv") as f:
        for row in csv.DictReader(f):
            if float(row["p"]) != 2.0:
                continue
            key = (int(row["model"]), int(row["pdg"]))
            q = float(row["child_p"])
            spectra[key].append(q)
            if q > 0:
                angles[key].append(float(row["cos_theta"]))
            else:
                zero_momentum += 1
    for angular in [False, True]:
        fig, axs = plt.subplots(3, 3, figsize=(11.7, 8.3))
        fig.suptitle(
            "Daughter angles at incident p=2 GeV/c"
            if angular
            else "Daughter momenta at incident p=2 GeV/c"
        )
        bins = (
            np.linspace(-1, 1, 21)
            if angular
            else np.array(
                [0, 0.001, 0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 10, np.inf]
            )
        )
        for ax, pdg, name in zip(axs.flat, channels, names):
            for mode in [0, 1]:
                n = len(groups[mode, pdg, 2.0])
                values = (
                    np.histogram((angles if angular else spectra)[mode, pdg], bins)[0]
                    / n
                )
                ax.stairs(
                    values,
                    bins if angular else np.arange(len(bins)),
                    color=colors[mode],
                    label=models[mode],
                )
            ax.set_title(name)
            ax.set_ylabel("Daughters / interaction / bin")
            if angular:
                ax.set_xlabel("cos(angle to incident direction)")
            else:
                ax.set_yscale("log")
                ax.set_xticks(
                    np.arange(11) + 0.5,
                    [
                        "0–1",
                        "1–5",
                        "5–20",
                        "20–50",
                        "50–100",
                        "100–200",
                        "200–500",
                        "500–1k",
                        "1k–2k",
                        "2k–10k",
                        ">10k",
                    ],
                    rotation=70,
                    fontsize=6,
                )
                ax.set_xlabel("Momentum bin [MeV/c]")
        axs.flat[0].legend(fontsize=8)
        fig.text(
            0.04,
            0.025,
            "All returned product species before prompt pi0 decay; target fragments remain in the residual. Absolute yield, no fitted normalization.\n"
            + (
                f"{zero_momentum} zero-momentum daughters have undefined angles and are omitted only from the angular distribution."
                if angular
                else "First and last bins include the low- and high-momentum tails."
            ),
            fontsize=8,
        )
        fig.tight_layout(rect=(0, 0.1, 1, 0.95))
        pdf.savefig(fig)
        plt.close(fig)
