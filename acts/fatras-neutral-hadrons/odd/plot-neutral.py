#!/usr/bin/env python3
"""Replot species attribution and neutral-cut checks from compact event summaries."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--results", type=Path, required=True)
a = p.parse_args()
keys = ["geant4", "charged-only", "fatras", "0mev", "50mev"]
rows = {
    k: json.loads((a.results / f"ancestry-{k}.json").read_text())["events"]
    for k in keys
}
n_events = len(rows["geant4"])
assert n_events >= 2
assert all([r["event"] for r in v] == list(range(n_events)) for v in rows.values())


def values(sample, key, sub=None):
    return np.array([r[key] if sub is None else r[key][sub] for r in rows[sample]])


def mean_se(x):
    return float(np.mean(x)), float(np.std(x, ddof=1) / np.sqrt(len(x)))


summary = {}
for k in keys:
    summary[k] = {
        name: dict(zip(["mean", "sem"], mean_se(values(k, name))))
        for name in ["primary", "secondary"]
    }
    summary[k]["nuclear_parent"] = {
        name: dict(zip(["mean", "sem"], mean_se(values(k, "nuclear_parent", name))))
        for name in rows[k][0]["nuclear_parent"]
    }
    x, y = values(k, "secondary"), values("geant4", "secondary")
    ratio = x.mean() / y.mean()
    error = np.std(x - ratio * y, ddof=1) / np.sqrt(len(x)) / y.mean()
    summary[k]["secondary_ratio_to_g4"] = {
        "ratio": float(ratio),
        "paired_sem": float(error),
    }
    for base in ["charged-only", "fatras"]:
        summary[k][f"secondary_gain_over_{base}"] = dict(
            zip(["mean", "paired_sem"], mean_se(x - values(base, "secondary")))
        )
(a.results / "neutral-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
book = PdfPages(a.results / "neutral_diagnostics.pdf")
footer = f"{n_events} matched ttbar + PU200 events; ODD pixels; hit-entry p ≥ 100 MeV, pT ≥ 50 MeV. Errors: event SEM."


def save(fig, name, caption):
    fig.text(0.5, 0.02, footer + "\n" + caption, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(a.results / f"{name}.pdf")
    book.savefig(fig)
    plt.close(fig)


fig, axes = plt.subplots(2, 1, figsize=(11, 8.5))
groups = list(rows["fatras"][0]["nuclear_parent"])
styles = [
    ("geant4", "Geant4 FTFP_BERT", "tab:blue"),
    ("charged-only", "Fatras: charged hadrons + V0", "grey"),
    ("fatras", "Fatras: + neutron / K-long", "tab:orange"),
]
x = np.arange(len(groups))
for i, (k, label, color) in enumerate(styles):
    means, errors = np.array(
        [mean_se(values(k, "nuclear_parent", g)) for g in groups]
    ).T
    axes[0].bar(x + (i - 1) * 0.25, means, 0.25, yerr=errors, label=label, color=color)
axes[0].set_xticks(x, ["anti-p / anti-n" if g == "antibaryon" else g for g in groups])
axes[0].set_ylabel("Nuclear-origin pixel hits / event")
axes[0].legend()
axes[0].set_title("Immediate nuclear parent: species attribution")
for k, label, color in styles:
    n = values(k, "nuclear_parent_z", "neutron") + values(
        k, "nuclear_parent_z", "K-long"
    )
    axes[1].errorbar(
        [250, 750, 1300],
        n.mean(axis=0),
        yerr=n.std(axis=0, ddof=1) / np.sqrt(len(n)),
        fmt="o-",
        label=label,
        color=color,
    )
axes[1].set_xticks([250, 750, 1300], ["0–500", "500–1000", "1000–1600"])
axes[1].set_xlabel("|hit z| region [mm]")
axes[1].set_ylabel("Neutron / K-long origin hits / event")
axes[1].legend()
axes[1].grid(alpha=0.2)
save(
    fig,
    "incident_species",
    "Immediate ancestry only. Geant4 nuclear category also includes non-inelastic processes; no inference from missing parent IDs.",
)

fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
x = np.arange(4)
cuts = ["charged-only", "0mev", "fatras", "50mev"]
labels = ["off", "0 MeV", "10 MeV", "50 MeV"]
means, errors = np.array([mean_se(values(k, "secondary")) for k in cuts]).T
axes[0].errorbar(
    x, means, yerr=errors, fmt="o", capsize=3, color="tab:orange", label="Fatras"
)
g4, se = mean_se(values("geant4", "secondary"))
axes[0].axhline(g4, color="tab:blue", label="Geant4")
axes[0].axhspan(g4 - se, g4 + se, alpha=0.15, color="tab:blue")
axes[0].set_ylabel("Secondary pixel hits / event")
axes[0].legend()
means, errors = np.array(
    [
        mean_se(values(k, "secondary") - values("charged-only", "secondary"))
        for k in cuts
    ]
).T
axes[1].errorbar(x, means, yerr=errors, fmt="o", capsize=3, color="tab:orange")
axes[1].axhline(0, color="black", lw=0.8)
axes[1].set_ylabel("Gain over charged-only [hits / event]")
for ax in axes:
    ax.set_xticks(x, labels)
    ax.set_xlabel("Neutral kinetic-energy cut")
    ax.grid(alpha=0.2)
fig.suptitle("Neutral transport acceptance: hit yield and paired differences")
save(
    fig,
    "neutral_acceptance",
    "1000 ns neutral global-time cut; tables cover 0.1–20 GeV/c. Input also has p ≥ 0.1 GeV/c; 0 MeV is not a full low-energy model.",
)
book.close()
