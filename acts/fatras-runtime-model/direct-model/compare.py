#!/usr/bin/env python3
"""Plot direct-model concurrency and physics checks, without transport or hit claims."""

import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def rows(path):
    if path.exists():
        with path.open() as f:
            yield from csv.DictReader(f)
    else:
        with gzip.open(path.with_suffix(".csv.gz"), "rt") as f:
            yield from csv.DictReader(f)


p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--scan", type=Path, required=True)
p.add_argument("--reference", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--machine-label", default="Hardware unspecified")
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
runs = json.loads((a.scan / "runs.json").read_text())
assert all(r["byte_identical_to_first_run"] for r in runs)
base = a.scan / runs[0]["directory"]
direct = list(rows(base / "events.csv"))
reference = list(rows(a.reference / "events.csv"))
groups = [defaultdict(list), defaultdict(list)]
for mode, events in enumerate([direct, reference]):
    for e in events:
        if mode == 0 and float(e["rate"]) == 0:
            continue  # zero cross-section grid point has no interaction to sample
        groups[mode][int(e["pdg"]), float(e["p"])].append(e)
assert set(groups[0]) == set(groups[1])
channels = [211, -211, 2212, 2112, 130, -2212, -2112, 321, -321]
names = ["π+", "π−", "p", "n", "KL", "anti-p", "anti-n", "K+", "K−"]
labels = ["Direct models, independent workers", "Existing Geant4 process adapter"]
colors = ["#008a75", "#4b68ac"]
fields = [
    ("multiplicity", "Nonnuclear particles / interaction"),
    ("charged", "Charged nonnuclear particles / interaction"),
    ("leading_fraction", "Leading nonnuclear particle energy / projectile energy"),
]
summary = {
    "runs": runs,
    "scope": "Isolated hadronic interactions in natural silicon; no detector transport or hit comparison",
    "physics": {},
}
for key, _ in fields:
    comparisons = []
    for point in sorted(groups[0]):
        x, y = [np.array([float(e[key]) for e in g[point]]) for g in groups]
        error = np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))
        z = (x.mean() - y.mean()) / error if error else 0.0
        comparisons.append(
            {
                "pdg": point[0],
                "p_GeV": point[1],
                "direct_mean": x.mean(),
                "reference_mean": y.mean(),
                "difference_SEM": error,
                "pull": z,
            }
        )
    summary["physics"][key] = comparisons
rate0 = {
    (int(r["pdg"]), float(r["p"])): float(r["rate"]) for r in rows(base / "rates.csv")
}
rate1 = {
    (int(r["pdg"]), float(r["p"])): float(r["live"])
    for r in rows(a.reference / "rates.csv")
}
assert rate0.keys() == rate1.keys()
relative = [abs(v - rate1[k]) / rate1[k] for k, v in rate0.items() if rate1[k] > 0]
assert all((v == 0) == (rate1[k] == 0) for k, v in rate0.items())
summary["max_relative_rate_difference"] = max(relative)
summary["output_identical_across_workers_and_reverse_order"] = True
summary["final_state_diagnostics"] = {}
for key in ["final_energy_error_MeV", "final_momentum_error_MeV", "final_charge_error"]:
    values = np.abs([float(r[key]) for r in direct])
    summary["final_state_diagnostics"][key] = {
        "max_abs": float(max(values)),
        "q99_abs": float(np.quantile(values, 0.99)),
    }
summary["final_state_diagnostics"]["mass_projections"] = sum(
    int(r["off_shell"]) for r in direct
)
summary["final_state_diagnostics"]["catastrophic_energy_results"] = sum(
    int(r["catastrophic"]) for r in direct
)
summary["worker_summary"] = []
for n in sorted({r["workers"] for r in runs}):
    rr = [r for r in runs if r["workers"] == n and not r["reverse"]]
    record = {"workers": n, "repeats": len(rr)}
    for key in ["sampling_wall_s", "sampling_cpu_s", "setup_wall_s", "peak_rss_MiB"]:
        v = [r[key] for r in rr]
        record[key] = float(np.median(v))
        record[key + "_range"] = [min(v), max(v)]
    summary["worker_summary"].append(record)
(a.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
plt.rcParams.update({"pdf.fonttype": 42, "font.size": 9})
footer = (
    f"{runs[0]['events_per_point']} direct samples / nonzero-rate point, nine projectile species, natural silicon. No daughter momentum cuts.\n"
    "Nuclear fragments are recorded but omitted from these nonnuclear spectra, as in Fatras residual handling. Error bars: sample SEM."
)
with PdfPages(a.output / "direct_model_validation.pdf") as pdf:
    fig, axs = plt.subplots(1, 3, figsize=(11.7, 7))
    fig.suptitle("Direct Geant4 models on independent C++ workers — 15 October 2026")
    w = summary["worker_summary"]
    workers = [r["workers"] for r in w]
    wall = np.array([r["sampling_wall_s"] for r in w])
    cpu = np.array([r["sampling_cpu_s"] for r in w])
    for key, label, color in [
        ("sampling_wall_s", "Wall time", "#008a75"),
        ("sampling_cpu_s", "Total process CPU", "#4b68ac"),
    ]:
        median = np.array([r[key] for r in w])
        bounds = np.array([r[key + "_range"] for r in w]).T
        axs[0].errorbar(
            workers,
            median,
            yerr=[median - bounds[0], bounds[1] - median],
            marker="o",
            label=label,
            color=color,
            capsize=3,
        )
    axs[0].set_ylabel("Sampling time [s]")
    axs[0].legend()
    axs[1].plot(workers, wall[0] / wall, "o-", color=colors[0], label="Measured")
    axs[1].plot(workers, workers, "--", color="grey", label="Ideal")
    axs[1].set_ylabel("Speedup vs one worker")
    axs[1].legend()
    axs[2].plot(workers, [r["peak_rss_MiB"] for r in w], "o-", color=colors[0])
    axs[2].set_ylabel("Peak RSS [MiB]")
    for ax in axs:
        ax.set_xlabel("Workers")
        ax.set_xticks(workers)
        ax.grid(alpha=0.2)
    fig.text(
        0.06,
        0.04,
        f"{runs[0]['calls']:,} generated interactions; same workload at every worker count. Median and range of sequential forward runs.\n"
        f"{a.machine_label}; {runs[0]['geant4_version'].strip('$')}. Initialization and CSV output excluded from sampling times.\n"
        "No Geant4 run manager, event loop or application lock around sampling. Particle workspace and model state per worker.\n"
        "All output CSVs byte-identical across worker counts, repeated runs and reverse scheduling. RSS includes retained validation products.\n"
        "This is a collision-generator benchmark, not Fatras event throughput or an inclusive-hit validation.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.23, 1, 0.94))
    pdf.savefig(fig)
    plt.close(fig)
    fig, axs = plt.subplots(3, 3, figsize=(11.7, 8.3))
    fig.suptitle(
        "Interaction rates: direct cross-section components vs existing adapter"
    )
    for ax, pdg, name in zip(axs.flat, channels, names):
        for mode, data in enumerate([rate0, rate1]):
            momenta = sorted(q for code, q in data if code == pdg)
            ax.plot(
                momenta,
                [data[pdg, q] for q in momenta],
                ".-",
                label=labels[mode],
                color=colors[mode],
            )
        ax.set_title(name)
        ax.set_xscale("log")
        ax.set_xlabel("Projectile p [GeV/c]")
        ax.set_ylabel("Rate × reference L0")
    axs.flat[0].legend(fontsize=7)
    fig.text(
        0.04,
        0.025,
        f"Maximum relative difference: {max(relative):.3g}. Same Geant4 projectile masses used in both probes; reference CSV has 12-digit precision.\nNatural silicon; tests component reuse, not arbitrary material mixtures or detector interactions.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    pdf.savefig(fig)
    plt.close(fig)
    for key, title in fields:
        fig, axs = plt.subplots(3, 3, figsize=(11.7, 8.3))
        fig.suptitle(title)
        for ax, pdg, name in zip(axs.flat, channels, names):
            for mode, g in enumerate(groups):
                momenta = sorted(q for code, q in g if code == pdg)
                v = [np.array([float(e[key]) for e in g[pdg, q]]) for q in momenta]
                ax.errorbar(
                    momenta,
                    [x.mean() for x in v],
                    yerr=[x.std(ddof=1) / np.sqrt(len(x)) for x in v],
                    marker=".",
                    color=colors[mode],
                    label=labels[mode],
                    capsize=2,
                )
            ax.set_xscale("log")
            ax.set_title(name)
            ax.set_xlabel("Projectile p [GeV/c]")
        axs.flat[0].legend(fontsize=7)
        fig.text(0.04, 0.025, footer, fontsize=8)
        fig.tight_layout(rect=(0, 0.1, 1, 0.95))
        pdf.savefig(fig)
        plt.close(fig)
    spectra = [defaultdict(list), defaultdict(list)]
    for mode, path in enumerate([base / "products.csv", a.reference / "products.csv"]):
        for row in rows(path):
            if float(row["p"]) != 2.0 or abs(int(row["child_pdg"])) >= 1000000000:
                continue
            spectra[mode][int(row["pdg"])].append(
                (float(row["child_p"]), float(row["cos_theta"]))
            )
    for angular in [False, True]:
        fig, axs = plt.subplots(3, 3, figsize=(11.7, 8.3))
        fig.suptitle(
            ("Daughter angles" if angular else "Daughter momenta")
            + " at projectile p=2 GeV/c"
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
                values = [
                    v[int(angular)]
                    for v in spectra[mode][pdg]
                    if not angular or v[0] > 0
                ]
                h = np.histogram(values, bins)[0] / len(groups[mode][pdg, 2.0])
                ax.step(
                    np.arange(len(h)),
                    h,
                    where="mid",
                    color=colors[mode],
                    label=labels[mode],
                )
            ax.set_title(name)
            ax.set_ylabel("Daughters / interaction / bin")
            if angular:
                ax.set_xticks([0, 5, 10, 15, 19], ["−1", "−0.5", "0", "0.5", "1"])
                ax.set_xlabel("cos θ relative to projectile")
            else:
                ax.set_xticks(
                    [0, 2, 4, 6, 8, 10],
                    ["0–.001", ".005–.02", ".05–.1", ".2–.5", "1–2", "≥10"],
                )
                ax.tick_params(axis="x", labelsize=7)
                ax.set_xlabel("Momentum bin [GeV/c]")
        axs.flat[0].legend(fontsize=7)
        fig.text(
            0.04,
            0.025,
            "No momentum cuts; momentum under/overflow included. Zero-momentum particles have no defined angle.\nNuclear fragments omitted from these nonnuclear spectra. Angular agreement also probes non-axial projectile rotations.",
            fontsize=8,
        )
        fig.tight_layout(rect=(0, 0.1, 1, 0.95))
        pdf.savefig(fig)
        plt.close(fig)
print(
    json.dumps(
        {
            "max_relative_rate_difference": max(relative),
            "max_abs_mean_pull": max(
                abs(r["pull"]) for key, _ in fields for r in summary["physics"][key]
            ),
            "worker_summary": summary["worker_summary"],
        },
        indent=2,
    )
)
