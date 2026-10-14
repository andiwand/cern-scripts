#!/usr/bin/env python3
"""Plot measured pion coverage, interaction frequency, conditional yields and material correction."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import uproot
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--diagnostics", type=Path, required=True)
p.add_argument("--coverage-results", type=Path, required=True)
p.add_argument("--map-results", type=Path, required=True)
p.add_argument("--original-map", type=Path, required=True)
p.add_argument("--corrected-map", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
styles = {
    "geant4": ("Geant4 FTFP_BERT", "tab:blue"),
    "baseline": ("Fatras: pion tables to 20 GeV", "grey"),
    "extended": ("Fatras: pion tables to 7 TeV", "tab:orange"),
    "corrected": ("Fatras: + corrected beam-pipe map", "tab:green"),
}
summary = {
    k: json.loads((a.diagnostics / f"{k}-pion-summary.json").read_text())
    for k in styles
}
rows = {k: v["events"] for k, v in summary.items()}
n = len(rows["geant4"])
assert all(len(v) == n for v in rows.values())
reactions = {
    k: pd.concat(
        [
            pd.read_csv(a.diagnostics / f"event{e:09d}-{k}-reactions.csv").assign(
                event=e
            )
            for e in range(n)
        ],
        ignore_index=True,
    )
    for k in styles
}
conditional = pd.concat(
    [pd.read_csv(a.diagnostics / f"event{e:09d}-conditional.csv") for e in range(n)],
    ignore_index=True,
)
r = reactions["geant4"]
assert len(r) == len(conditional)
r["model_accepted"] = conditional.mean_accepted
bins = np.asarray(summary["geant4"]["momentum_bins"])
centers = np.sqrt(bins[1:-2] * bins[2:-1])
book = PdfPages(a.output / "pion_diagnostics.pdf")
footer = f"{n} matched ttbar + PU200 ODD tracker events; Bz=2 T. Common pixel-hit cuts: p ≥100 MeV, pT ≥50 MeV."


def save(fig, name, caption):
    fig.text(0.5, 0.015, footer + "\n" + caption, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 0.96))
    fig.savefig(a.output / f"{name}.pdf")
    book.savefig(fig)
    plt.close(fig)


def meanse(x):
    return np.mean(x, axis=0), np.std(x, axis=0, ddof=1) / np.sqrt(len(x))


fig, ax = plt.subplots(1, 2, figsize=(12, 5.5))
for k, (label, color) in styles.items():
    x = np.array([v["interaction_hit_momentum_hist"] for v in rows[k]])[:, 1:-1]
    mean, se = meanse(x)
    ax[0].stairs(mean, bins[1:-1], color=color, label=label)
    ax[0].fill_between(centers, mean - se, mean + se, color=color, alpha=0.15)
    totals = np.array([v["primary_pion_p_hist"] for v in rows[k]])[:, 1:-1]
    inter = np.array([v["primary_inelastic_p_hist"] for v in rows[k]])[:, 1:-1]
    ratio = inter.sum(axis=0) / np.maximum(totals.sum(axis=0), 1)
    ax[1].plot(centers, ratio, "o-", color=color, label=label)
for axis in ax:
    axis.set_xscale("log")
    axis.grid(alpha=0.2)
    axis.legend(fontsize=8)
ax[0].set_xlabel("Incident momentum [GeV/c]")
ax[0].set_ylabel("Inelastic-origin pixel hits / event / bin")
ax[0].axvline(20, color="black", ls=":")
ax[1].set_xlabel("Generator-pion initial momentum [GeV/c]")
ax[1].set_ylabel("Fraction with an inelastic interaction")
fig.suptitle("Pion coverage and interaction frequency")
save(
    fig,
    "pion_coverage",
    "G4 incident momentum is pre-step; Fatras is at sampling after EM loss. Left: event SEM. Right: includes transport/material differences.",
)

fig, ax = plt.subplots(1, 2, figsize=(12, 5.5))
keys = [
    "in-domain accepted",
    "parent above 20 GeV",
    "parent below transport cuts",
    "daughter below production cuts",
    "nuclear fragment",
    "elastic",
    "at-rest capture",
    "unmatched vertex",
]
labels = [
    "in domain",
    "parent >20",
    "parent cut",
    "daughter cut",
    "fragments",
    "elastic",
    "capture",
    "unmatched",
]
x = np.arange(len(keys))
for i, k in enumerate(styles):
    y = np.array([[row["hit_categories"][key] for key in keys] for row in rows[k]])
    mean, se = meanse(y)
    ax[0].bar(
        x + (i - 1.5) * 0.2, mean, 0.2, yerr=se, label=styles[k][0], color=styles[k][1]
    )
ax[0].set_xticks(x, labels, rotation=35, ha="right")
ax[0].set_yscale("symlog", linthresh=10)
ax[0].set_ylabel("Pion nuclear-origin pixel hits / event")
ax[0].legend(fontsize=7)
selected = (r.subtype == 121) & (r.p >= 0.1) & (r.p <= 7000) & (r.pt >= 0.05)
rr = r.loc[selected]
hist_bins = np.array([0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 1000, 7000])
which = np.digitize(rr.p, hist_bins) - 1
for field, label, color in [
    ("inclusive_accepted", "Geant4 actual detector materials", "tab:blue"),
    ("model_accepted", "Si library at the same incident kinematics", "tab:orange"),
]:
    means = [rr.loc[which == i, field].mean() for i in range(len(hist_bins) - 1)]
    ax[1].stairs(means, hist_bins, label=label, color=color)
ax[1].set_xscale("log")
ax[1].set_xlabel("Incident pre-step momentum [GeV/c]")
ax[1].set_ylabel("Accepted charged products / interaction")
ax[1].grid(alpha=0.2)
ax[1].legend(fontsize=7)
fig.suptitle("Separate missing coverage from conditional daughter yield")
save(
    fig,
    "pion_yields",
    "Right: production p/pT cuts, excluding nuclear fragments; includes surviving leading pions. 64 Si samples per G4 collision; not a hit prediction.",
)

fig, ax = plt.subplots(1, 2, figsize=(12, 5.5))
prefix = "SurfaceMaterial_vol2_bou0_lay2_app0_sen0/"
for path, label, color in [
    (a.original_map, "Original map", "grey"),
    (a.corrected_map, "Known Be slab in empty bins", "tab:green"),
]:
    f = uproot.open(path)
    t = f[prefix + "t"].values()
    l = f[prefix + "l0"].values()
    v = np.divide(t, l, out=np.zeros_like(t), where=l > 0).mean(axis=0)
    z = np.linspace(-4001, 4001, 11)
    ax[0].stairs(v, z, label=label, color=color)
ax[0].set_xlabel("Beam-pipe z [mm]")
ax[0].set_ylabel("Normal-incidence thickness / L0")
ax[0].legend(fontsize=8)
ax[0].grid(alpha=0.2)
z_bins = np.array([0, 400, 800, 1200, 1600, 2400, 3200, 4002])
for k, (label, color) in styles.items():
    q = reactions[k]
    m = (q.subtype == 121) & (np.hypot(q.x, q.y) < 25)
    mean = (
        np.histogram(np.abs(q.loc[m, "z"]), z_bins, weights=q.loc[m, "truth_hits"])[0]
        / n
    )
    ax[1].stairs(mean, z_bins, label=label, color=color)
ax[1].set_xlabel("|interaction z| for r<25 mm [mm]")
ax[1].set_ylabel("Direct pion-secondary pixel hits / event / bin")
ax[1].legend(fontsize=7)
ax[1].grid(alpha=0.2)
fig.suptitle("Beam-pipe material coverage: a geometry-input correction")
save(
    fig,
    "beampipe_coverage",
    "1152/1440 bins empty originally. Fill only those bins with the physical 0.8 mm Be pipe; sampled central bins and all other map values remain intact.",
)

fig, ax = plt.subplots(1, 2, figsize=(12, 5.5))
mid = json.loads((a.coverage_results / "high-midpoint-comparison.json").read_text())
calstats = {}
for pdg, label, color in [(211, "pi+", "tab:blue"), (-211, "pi−", "tab:orange")]:
    v = [d for d in mid if d["pdg"] == pdg]
    pvals = np.array([d["p_GeV"] for d in v])
    bias = np.array([d["model_rate"] / d["reference_rate"] - 1 for d in v])
    delta = np.array([d["model_charged_mean"] - d["reference_charged_mean"] for d in v])
    err = [np.hypot(d["model_charged_se"], d["reference_charged_se"]) for d in v]
    ax[0].plot(pvals, 100 * bias, ".-", color=color, label=label)
    ax[1].errorbar(pvals, delta, yerr=err, fmt=".", color=color, label=label)
    calstats[str(pdg)] = {
        "max_abs_rate_bias": float(max(abs(bias))),
        "mean_multiplicity_delta": float(delta.mean()),
    }
for axis in ax:
    axis.set_xscale("log")
    axis.set_xlabel("Incident momentum [GeV/c]")
    axis.axhline(0, color="black", lw=0.8)
    axis.legend()
    axis.grid(alpha=0.2)
ax[0].set_ylabel("Interpolated / reference rate − 1 [%]")
ax[1].set_ylabel("Library − reference charged multiplicity")
fig.suptitle("Independent validation of the high-momentum extension")
save(
    fig,
    "high_calibration",
    "52 added nodes/species to 7 TeV; 512 training events/node; 256 independent events/midpoint. Errors: MC standard errors; multiplicity before cuts.",
)
book.close()

# Event-paired totals for all three Fatras variants.
paths = {
    "geant4": (a.coverage_results, "geant4"),
    "baseline": (a.coverage_results, "fatras-em"),
    "extended": (a.coverage_results, "fatras"),
    "corrected": (a.map_results, "fatras"),
}
event_totals = {
    k: json.loads((directory / f"{name}-20.json").read_text())
    for k, (directory, name) in paths.items()
}
ref = np.array([x["pixel_common_secondary_hits"] for x in event_totals["geant4"]])
stats = {}
for k, v in event_totals.items():
    sec = np.array([x["pixel_common_secondary_hits"] for x in v])
    pri = np.array([x["pixel_common_primary_hits"] for x in v])
    ratio = sec.mean() / ref.mean()
    stats[k] = {
        "primary": float(pri.mean()),
        "secondary": float(sec.mean()),
        "secondary_ratio": float(ratio),
        "ratio_paired_sem": float(
            np.std(sec - ratio * ref, ddof=1) / np.sqrt(n) / ref.mean()
        ),
        "gains": {},
    }
    for baseline in ["baseline", "extended"]:
        d = sec - np.array(
            [x["pixel_common_secondary_hits"] for x in event_totals[baseline]]
        )
        m, e = meanse(d)
        stats[k]["gains"][baseline] = {"mean": float(m), "paired_sem": float(e)}
conditional_stats = {}
for lo, hi, label in [(0.1, 20, "old_domain"), (20, 7000, "extension")]:
    m = selected & (r.p >= lo) & (r.p <= hi)
    conditional_stats[label] = {
        "interactions": int(sum(m)),
        "geant4_mean_accepted": float(r.loc[m, "inclusive_accepted"].mean()),
        "si_mean_accepted": float(r.loc[m, "model_accepted"].mean()),
    }
(a.output / "pion-study-summary.json").write_text(
    json.dumps(
        {
            "hits": stats,
            "conditional": conditional_stats,
            "calibration": calstats,
            "pion_hit_categories": {
                k: {
                    c: float(np.mean([e["hit_categories"][c] for e in v]))
                    for c in v[0]["hit_categories"]
                }
                for k, v in rows.items()
            },
            "caveats": [
                "Conditional yields are for accepted non-fragment products, not downstream hits.",
                "G4 uses pre-step incident momentum; continuous energy loss within that step is not resolved.",
                "30 G4 pion-origin hits across 20 events have no matched vertex and remain explicit.",
                "First-interaction probabilities include material, decay and transport-acceptance differences.",
            ],
        },
        indent=2,
    )
    + "\n"
)
