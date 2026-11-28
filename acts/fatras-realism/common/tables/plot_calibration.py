#!/usr/bin/env python3
"""Plot rate bias and charged multiplicity of compare.py outputs per projectile.

  plot_calibration.py holdout=holdout-comparison.json midpoint=midpoint-comparison.json \
      --output calibration.pdf
Also writes OUTPUT.json with per-projectile summaries.
"""

import argparse
import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NAMES = {211: "pi+", -211: "pi-", 2212: "p", -2212: "anti-p", 2112: "n",
         -2112: "anti-n", 130: "K-long", 321: "K+", -321: "K-"}

p = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
p.add_argument("comparisons", nargs="+", help="LABEL=compare.py JSON")
p.add_argument("--output", type=Path, required=True)
p.add_argument("--title", default="Calibration against independent Geant4 samples")
a = p.parse_args()
data = {}
for item in a.comparisons:
    label, path = item.split("=", 1)
    data[label] = json.loads(Path(path).read_text())
pdgs = sorted({r["pdg"] for rows in data.values() for r in rows}, key=abs)
fig, axes = plt.subplots(2, len(pdgs), figsize=(5.5 * len(pdgs), 8), sharex=True, squeeze=False)
summary = {}
for column, pdg in enumerate(pdgs):
    label = NAMES.get(pdg, str(pdg))
    summary[label] = {}
    for name, rows in data.items():
        rows = [r for r in rows if r["pdg"] == pdg]
        if not rows:
            continue
        x = np.array([r["p_GeV"] for r in rows])
        bias = np.array([r["model_rate"] / r["reference_rate"] - 1 for r in rows])
        delta = np.array([r["model_charged_mean"] - r["reference_charged_mean"] for r in rows])
        se = np.array([np.hypot(r["model_charged_se"], r["reference_charged_se"]) for r in rows])
        axes[0, column].plot(x, 100 * bias, ".-", label=name)
        axes[1, column].errorbar(x, delta, yerr=se, fmt=".", label=name, alpha=0.8)
        summary[label][name] = {
            "max_absolute_rate_bias": float(max(abs(bias))),
            "mean_charged_multiplicity_difference": float(delta.mean()),
            "charged_multiplicity_difference_range": [float(delta.min()), float(delta.max())],
        }
    axes[0, column].set_title(label)
    axes[1, column].set_xlabel("Incident momentum [GeV]")
    for ax in axes[:, column]:
        ax.set_xscale("log")
        ax.axhline(0, color="black", lw=0.8)
        ax.grid(alpha=0.2)
        ax.legend()
axes[0, 0].set_ylabel("Interpolated rate / reference - 1 [%]")
axes[1, 0].set_ylabel("Library - reference charged multiplicity")
fig.suptitle(a.title)
fig.text(
    0.5,
    0.015,
    "Errors: MC standard errors. Multiplicity is before transport cuts.",
    ha="center",
    fontsize=9,
)
fig.tight_layout(rect=(0, 0.05, 1, 0.96))
fig.savefig(a.output)
a.output.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
