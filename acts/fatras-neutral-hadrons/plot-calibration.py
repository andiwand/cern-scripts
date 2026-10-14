#!/usr/bin/env python3
"""Plot independent-node and midpoint calibration diagnostics."""
import argparse
import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--data", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)
summary = {}
for column, (pdg, label) in enumerate([(2112, "Neutron"), (130, "K-long")]):
    summary[label] = {}
    for name, color in [("holdout", "tab:blue"), ("midpoint", "tab:orange")]:
        rows = [
            r
            for r in json.loads((a.data / f"{name}-comparison.json").read_text())
            if r["pdg"] == pdg
        ]
        x = np.array([r["p_GeV"] for r in rows])
        bias = np.array([r["model_rate"] / r["reference_rate"] - 1 for r in rows])
        delta = np.array(
            [r["model_charged_mean"] - r["reference_charged_mean"] for r in rows]
        )
        se = np.array(
            [np.hypot(r["model_charged_se"], r["reference_charged_se"]) for r in rows]
        )
        axes[0, column].plot(x, 100 * bias, ".-", label=name, color=color)
        axes[1, column].errorbar(
            x, delta, yerr=se, fmt=".", label=name, color=color, alpha=0.8
        )
        summary[label][name] = {
            "max_absolute_rate_bias": float(max(abs(bias))),
            "mean_charged_multiplicity_difference": float(delta.mean()),
            "charged_multiplicity_difference_range": [
                float(delta.min()),
                float(delta.max()),
            ],
        }
    axes[0, column].set_title(label)
    axes[1, column].set_xlabel("Incident momentum [GeV]")
    for ax in axes[:, column]:
        ax.set_xscale("log")
        ax.axhline(0, color="black", lw=0.8)
        ax.grid(alpha=0.2)
        ax.legend()
axes[0, 0].set_ylabel("Interpolated rate / reference − 1 [%]")
axes[1, 0].set_ylabel("Library − reference charged multiplicity")
fig.suptitle("Si reference calibration: independent samples, Geant4 11.3.2 FTFP_BERT")
fig.text(
    0.5,
    0.015,
    "512 training events/node; 256 independent reference events/node or midpoint; 48 log-spaced nodes, 0.1–20 GeV.\nErrors: MC standard errors. Node rates are identical by construction. Multiplicity is before transport cuts.",
    ha="center",
    fontsize=9,
)
fig.tight_layout(rect=(0, 0.06, 1, 0.96))
fig.savefig(a.output)
a.output.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
