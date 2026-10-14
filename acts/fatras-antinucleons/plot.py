#!/usr/bin/env python3
"""Plot matched antinucleon hit gains, reference scope, and independent calibration."""

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
p.add_argument("--calibration", type=Path, required=True)
a = p.parse_args()
rows = {
    k: json.loads((a.results / f"{k}-ancestry.json").read_text())["events"]
    for k in ["geant4", "baseline", "fatras"]
}
n = len(rows["geant4"])
assert n > 1 and all([v["event"] for v in r] == list(range(n)) for r in rows.values())
secondary = {k: np.array([v["secondary_hits"] for v in r]) for k, r in rows.items()}
primary = {k: np.array([v["primary_hits"] for v in r]) for k, r in rows.items()}


def sem(x):
    return float(np.std(x, ddof=1) / np.sqrt(n))


def direct(k, pdgs):
    return np.array(
        [sum(v["nuclear_parent_hits"].get(str(p), 0) for p in pdgs) for v in rows[k]]
    )


summary = {"events": n, "hits": {}, "calibration": {}}
for k, x in secondary.items():
    ratio = x.mean() / secondary["geant4"].mean()
    summary["hits"][k] = {
        "primary": float(primary[k].mean()),
        "secondary": float(x.mean()),
        "secondary_ratio": float(ratio),
        "ratio_paired_sem": sem(x - ratio * secondary["geant4"])
        / secondary["geant4"].mean(),
        "antinucleon_direct": float(direct(k, [-2212, -2112]).mean()),
    }
gain = secondary["fatras"] - secondary["baseline"]
summary["gain"] = {
    "mean": float(gain.mean()),
    "paired_sem": sem(gain),
    "relative": float(gain.mean() / secondary["baseline"].mean()),
}
cats = [
    "in-flight, within model cuts",
    "at-rest annihilation",
    "nuclear fragment",
    "parent below transport cuts",
    "outside table momentum range",
    "daughter below production cuts",
    "elastic",
    "unmatched vertex",
    "ambiguous vertex",
]
summary["reference_categories"] = {
    k: float(np.mean([v["geant4_categories"].get(k, 0) for v in rows["geant4"]]))
    for k in cats
}
summary["reference_interactions"] = {
    k: sum(v["geant4_process_interactions"].get(k, 0) for v in rows["geant4"])
    for k in set().union(*(v["geant4_process_interactions"] for v in rows["geant4"]))
}
labels = {
    "geant4": "Geant4 FTFP_BERT",
    "baseline": "Fatras before",
    "fatras": "Fatras + antinucleons",
}
colors = {"geant4": "tab:blue", "baseline": "grey", "fatras": "tab:orange"}
caption = f"{n} matched ttbar + PU200 events; ODD pixels; Bz = 2 T. Hit-entry p ≥ 100 MeV, pT ≥ 50 MeV."
with PdfPages(a.results / "antinucleon_diagnostics.pdf") as book:

    def save(fig, name, foot, study_caption=caption):
        fig.text(0.5, 0.025, study_caption + "\n" + foot, ha="center", fontsize=9)
        fig.tight_layout(rect=(0, 0.11, 1, 0.94))
        book.savefig(fig)
        fig.savefig(a.results / f"{name}.pdf")
        fig.savefig(a.results / f"{name}.png", dpi=140)
        plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    for i, k in enumerate(labels):
        ax[0].bar(
            i, secondary[k].mean(), color=colors[k], yerr=sem(secondary[k]), capsize=4
        )
        ax[0].text(
            i, secondary[k].mean() + 350, f"{secondary[k].mean():,.0f}", ha="center"
        )
    ax[0].set_xticks(range(3), list(labels.values()), rotation=15)
    ax[0].set_ylabel("Secondary pixel hits / event")
    ax[0].set_ylim(0, 20500)
    groups = [
        ("π±", [211, -211]),
        ("p̄", [-2212]),
        ("n̄", [-2112]),
        ("K±", [321, -321]),
        ("n / KL", [2112, 130]),
        ("p", [2212]),
    ]
    for i, k in enumerate(labels):
        ax[1].bar(
            np.arange(len(groups)) + (i - 1) * 0.25,
            [direct(k, pdgs).mean() for _, pdgs in groups],
            width=0.25,
            color=colors[k],
            label=labels[k],
        )
    ax[1].set_xticks(range(len(groups)), [name for name, _ in groups])
    ax[1].set_ylabel("Nuclear-origin pixel hits / event")
    ax[1].legend(fontsize=8)
    fig.suptitle(
        f"Antinucleon addition: +{gain.mean():.0f} ± {sem(gain):.0f} secondary hits/event (paired SEM)"
    )
    save(
        fig,
        "hit_gain",
        "Same corrected material map and previous channels. Immediate-parent categories; no rate or multiplicity tuning.",
    )
    fig, ax = plt.subplots(
        1, 2, figsize=(12, 6), gridspec_kw={"width_ratios": [1.5, 1]}
    )
    y = np.arange(len(cats))
    vals = [summary["reference_categories"][k] for k in cats]
    ax[0].barh(y, vals, color=["tab:blue"] + ["grey"] * (len(cats) - 1))
    ax[0].set_yticks(y, cats, fontsize=9)
    ax[0].invert_yaxis()
    ax[0].set_xlabel("Geant4 antinucleon-origin pixel hits / event")
    ax[0].set_xlim(0, 760)
    for yy, val in zip(y, vals):
        ax[0].text(val + 5, yy, f"{val:.2f}", va="center", fontsize=9)
    text = (
        f"Reference, all hadronic processes: {summary['hits']['geant4']['antinucleon_direct']:.2f} hits/event\n"
        f"Within current model cuts: {vals[0]:.2f}\nFatras direct antinucleon daughters: {summary['hits']['fatras']['antinucleon_direct']:.2f}\n\n"
        f"Total secondary coverage:\n{100*summary['hits']['baseline']['secondary_ratio']:.2f}% → {100*summary['hits']['fatras']['secondary_ratio']:.2f}% of Geant4\n\n"
        "No at-rest transport or annihilation.\nNo fragment transport or elastic model.\nSi final states with local-L0 scaling.\nG4 incident momentum is pre-step.\nUnmatched vertices remain explicit."
    )
    ax[1].axis("off")
    ax[1].text(0.02, 0.95, text, va="top", fontsize=11, linespacing=1.6)
    fig.suptitle("What the antinucleon channels cover")
    save(
        fig,
        "reference_scope",
        "Net gain includes changed cascades and RNG history; direct daughter hits are not the net recoverable gain.",
    )
    calibration = json.loads(a.calibration.read_text())
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex="col")
    for col, (pdg, name) in enumerate([(-2212, "Antiproton"), (-2112, "Antineutron")]):
        rr = [r for r in calibration if r["pdg"] == pdg]
        x = np.array([r["p_GeV"] for r in rr])
        bias = np.array([r["model_rate"] / r["reference_rate"] - 1 for r in rr])
        delta = np.array(
            [r["model_charged_mean"] - r["reference_charged_mean"] for r in rr]
        )
        err = [np.hypot(r["model_charged_se"], r["reference_charged_se"]) for r in rr]
        axes[0, col].plot(x, 100 * bias, ".-")
        axes[1, col].errorbar(x, delta, yerr=err, fmt=".", alpha=0.6)
        axes[0, col].set_title(name)
        axes[1, col].set_xlabel("Incident momentum [GeV/c]")
        for axis in axes[:, col]:
            axis.set_xscale("log")
            axis.axhline(0, color="black", lw=0.8)
            axis.grid(alpha=0.2)
        summary["calibration"][str(pdg)] = {
            "max_abs_rate_bias": float(abs(bias).max()),
            "mean_charged_multiplicity_delta": float(delta.mean()),
            "multiplicity_delta_range": [float(delta.min()), float(delta.max())],
        }
    axes[0, 0].set_ylabel("Interpolated rate / reference − 1 [%]")
    axes[1, 0].set_ylabel("Library − reference charged multiplicity")
    fig.suptitle("Independent midpoint checks: silicon, Geant4 11.3.2 FTFP_BERT")
    save(
        fig,
        "calibration",
        "100 nodes/species, 512 samples/node; 99 independent midpoints/species, 256 samples/point.",
        "Independent silicon collisions; errors: Monte Carlo standard errors; multiplicity before transport cuts.",
    )
(a.results / "antinucleon-summary.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
print(json.dumps(summary, indent=2))
