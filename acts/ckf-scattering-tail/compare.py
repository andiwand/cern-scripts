#!/usr/bin/env python3
"""Three-mode rates and robust perigee resolutions; inclusive and common truth."""
import argparse
import json
from pathlib import Path

import awkward as ak
import matplotlib
import numpy as np
import uproot
from scipy.stats import beta

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator

p = argparse.ArgumentParser()
p.add_argument("run", type=Path)
a = p.parse_args()
config = json.loads((a.run / "config.json").read_text())
rates = json.loads((a.run / "rates.json").read_text())
modes = {
    "core15": ("No tail handling", "black"),
    "tail": ("Previous: tail model", "tab:blue"),
    "tail80": ("New: tail + T ≤ 80", "tab:red"),
}
barcodes = [
    "vertex_primary",
    "vertex_secondary",
    "particle",
    "generation",
    "sub_particle",
]
parameters = {
    "d0": ("LOC0", 1000, "d0 [µm]"),
    "z0": ("LOC1", 1000, "z0 [µm]"),
    "phi": ("PHI", 1000, "phi [mrad]"),
    "theta": ("THETA", 1000, "theta [mrad]"),
}
labels = {k: v[2] for k, v in parameters.items()}
labels.update(qop_relative="Relative q/p [%]", pt_relative="Relative pT [%]")
pt_edges = np.array([1, 1.5, 2, 3, 5, 10, 20, 50, 100])
data = {}
for mode in modes:
    arr = uproot.open(a.run / f"{mode}_ambi_tracks.root")["tracksummary"].arrays()
    flat = {
        k: ak.to_numpy(ak.flatten(arr[k]))
        for k in arr.fields
        if k not in ["event_nr"] and arr[k].ndim == 2
    }
    event = np.repeat(
        ak.to_numpy(arr["event_nr"]), ak.to_numpy(ak.num(arr["track_nr"]))
    )
    keys = list(zip(event, *(flat["majorityParticleId_" + b] for b in barcodes)))
    # Exactly one best matched track per selected truth particle. The writer
    # fills truth kinematics only for its selected input-particle collection.
    matched = (flat["trackClassification"] == 1) & np.isfinite(flat["t_pT"])
    residuals = {k: flat[f"res_e{v[0]}_fit"] * v[1] for k, v in parameters.items()}
    with np.errstate(divide="ignore", invalid="ignore"):
        residuals["qop_relative"] = (
            100 * flat["res_eQOP_fit"] * flat["t_p"] / flat["t_charge"]
        )
        # These runs use unit-charge (muon-hypothesis) fits.
        fit_pt = np.sin(flat["eTHETA_fit"]) / np.abs(flat["eQOP_fit"])
        residuals["pt_relative"] = 100 * (fit_pt / flat["t_pT"] - 1)
    data[mode] = dict(flat=flat, keys=keys, matched=matched, residuals=residuals)
common = set.intersection(
    *({k for k, m in zip(d["keys"], d["matched"]) if m} for d in data.values())
)


def widths(values):
    assert np.isfinite(values).all(), "Nonfinite fitted residual"
    if len(values) < 30:
        return {"n": len(values), "median": None, "width68": None, "width95": None}
    q = np.quantile(values, [0.025, 0.15865, 0.5, 0.84135, 0.975])
    return dict(
        n=len(values),
        median=float(q[2]),
        width68=float((q[3] - q[1]) / 2),
        width95=float((q[4] - q[0]) / 2),
    )


summary = {"common_particles": len(common), "modes": {}}
for mode, d in data.items():
    common_mask = d["matched"] & np.array([k in common for k in d["keys"]])
    summary["modes"][mode] = {
        "inclusive": {k: widths(v[d["matched"]]) for k, v in d["residuals"].items()},
        "common": {k: widths(v[common_mask]) for k, v in d["residuals"].items()},
        "vs_pt": {
            k: [
                widths(
                    v[
                        d["matched"]
                        & (d["flat"]["t_pT"] >= low)
                        & (d["flat"]["t_pT"] < high)
                    ]
                )
                for low, high in zip(pt_edges[:-1], pt_edges[1:])
            ]
            for k, v in d["residuals"].items()
        },
    }
summary["pt_edges"] = pt_edges.tolist()
(a.run / "resolutions.json").write_text(
    json.dumps(summary, indent=2, allow_nan=False) + "\n"
)

fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
for mode, (label, color) in modes.items():
    for row, prefix in enumerate(["trackeff", "fakeRatio"]):
        for col, variable in enumerate(["pT", "eta"]):
            h = rates[mode][f"{prefix}_vs_{variable}"]
            edges = np.array(h["edges"])
            boundaries = [0, 1, 2, 4, 40] if variable == "pT" else list(range(0, 41, 2))
            k = np.array(
                [sum(h["passed"][i:j]) for i, j in zip(boundaries[:-1], boundaries[1:])]
            )
            n = np.array(
                [sum(h["total"][i:j]) for i, j in zip(boundaries[:-1], boundaries[1:])]
            )
            x = (edges[boundaries[:-1]] + edges[boundaries[1:]]) / 2
            if variable == "pT":
                x = np.sqrt(
                    np.maximum(1, edges[boundaries[:-1]]) * edges[boundaries[1:]]
                )
            mask = n > 0
            k, n, x = k[mask], n[mask], x[mask]
            y = k / n
            # 68.27% Clopper-Pearson intervals; counters from the ROOT writer.
            low = np.where(k > 0, beta.ppf(0.15865, k, n - k + 1), 0)
            high = np.where(k < n, beta.ppf(0.84135, k + 1, n - k), 1)
            ax = axes[row, col]
            ax.errorbar(
                x,
                100 * y,
                yerr=100 * np.array([y - low, high - y]),
                fmt=".-",
                color=color,
                label=label,
                lw=1,
                ms=4,
            )
            ax.set_xlabel(
                ("Truth " if row == 0 else "Reconstructed ")
                + ("pT [GeV]" if variable == "pT" else "eta")
            )
            ax.set_ylabel(
                "Efficiency [%]" if row == 0 else "Fake tracks / all tracks [%]"
            )
            ax.grid(alpha=0.2)
            if variable == "pT":
                ax.set_xscale("log")
                ax.set_xlim(1, 100)
            else:
                ax.set_xlim(-3, 3)
axes[0, 0].legend(fontsize=9)
fig.suptitle(
    f"ODD pileup {config['pu']}, {config['events']} events; after ambiguity resolution"
)
fig.savefig(a.run / "three_modes_rates.png", dpi=180)
fig.savefig(a.run / "three_modes_rates.pdf")
plt.close(fig)

fig, axes = plt.subplots(2, 3, figsize=(12, 7), layout="constrained")
for ax, quantity in zip(axes.flat, labels):
    for mode, (label, color) in modes.items():
        bins = summary["modes"][mode]["vs_pt"][quantity]
        x = np.sqrt(pt_edges[:-1] * pt_edges[1:])
        for width, style in [("width68", "-"), ("width95", "--")]:
            y = [b[width] if b[width] is not None else np.nan for b in bins]
            ax.plot(
                x,
                y,
                style,
                color=color,
                marker=".",
                lw=1,
                label=label if width == "width68" else None,
            )
    ax.set_xscale("log")
    right = max(
        pt_edges[i + 1]
        for mode in modes
        for i, b in enumerate(summary["modes"][mode]["vs_pt"][quantity])
        if b["width68"] is not None
    )
    ticks = [t for t in [1, 2, 5, 10, 20, 50, 100] if t <= right]
    ax.set_xticks(ticks, labels=[str(t) for t in ticks])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(1, right)
    ax.set_yscale("log")
    ax.set_xlabel("Truth pT [GeV]")
    ax.set_ylabel("Residual half-width: " + labels[quantity])
    ax.grid(alpha=0.2)
axes[0, 0].legend(fontsize=8)
fig.suptitle(
    f"ODD pileup {config['pu']}: matched selected truth; solid 68.27%, dashed 95%\n"
    "Central quantile widths (not Gaussian fits); bins require ≥30 tracks",
    fontsize=11,
)
fig.savefig(a.run / "three_modes_resolutions.png", dpi=180)
fig.savefig(a.run / "three_modes_resolutions.pdf")
