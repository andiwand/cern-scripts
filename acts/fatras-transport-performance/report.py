"""Inclusive hit and CPU comparison, with separate deterministic probe checks."""

import argparse
import collections
import csv
import hashlib
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import math

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--reference", type=Path, default=Path.home() / "cern/scripts/acts/fatras-soft-secondaries/results/2026-10-15/summary.json")
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
old = json.loads(a.reference.read_text())
ids = ["particle_id_" + k for k in ["pv", "sv", "part", "gen", "subpart"]]
def open_csv(path):
    return path.open() if path.exists() else gzip.open(path.with_suffix(".csv.gz"), "rt")


def csv_hashes(path):
    hashes = {}
    files = list(path.glob("event*.csv")) + list(path.glob("event*.csv.gz"))
    for f in files:
        opener = gzip.open if f.suffix == ".gz" else open
        with opener(f, "rb") as stream:
            hashes[f.name.removesuffix(".gz")] = hashlib.file_digest(stream, "sha256").hexdigest()
    if not hashes:
        hashes = json.loads((path / "csv-hashes.json").read_text())
    return hashes


ptbins = [0, .001, .005, .02, .05, .1, .2, .5, 1, 2, 10, 100, np.inf]
names = {"pruned-check": "Optimised navigation", "helix-refine": "Helix 0.25 rad (experimental)", "helix-fine": "Helix 0.05 rad (experimental)"}
result = {"scope": "Three identical ttbar + PU200 events, 2 T, physical ODD ID. All written hits, no analysis cuts. Charged p>=0.2 MeV, pT>=0.05 MeV; four-turn and 50000-step budgets remain. Main CPU archived on five events, other physics comparisons on three; repeat timings reuse those three events.", "runs": {}, "summary": {}}
for name in ["ACTS main", "Bounded: softer transport", "Geant4 default, ID only"]:
    result["runs"][name] = old["runs"][name]
    result["summary"][name] = old["summary"][name]
for folder, name in names.items():
    path = a.work / folder
    meta = json.loads((path / "metadata.json").read_text())
    events = []
    for ev in range(3):
        stem = f"event{ev:09d}"
        with open_csv(path / (stem + "-particles_simulated.csv")) as f:
            truth = {tuple(r[k] for k in ids): r["process"] for r in csv.DictReader(f)}
        counts = collections.Counter()
        processes = collections.Counter()
        pts = []
        with open_csv(path / (stem + "-hits.csv")) as f:
            for h in csv.DictReader(f):
                assert math.hypot(float(h["tx"]), float(h["ty"])) <= 1202.001
                assert abs(float(h["tz"])) <= 4002.001
                pixel = int(h["geometry_id"]) >> 56 in [16, 17, 18]
                secondary = int(h["particle_id_gen"]) > 0
                suffix = "secondary" if secondary else "primary"
                counts["ID_" + suffix] += 1
                counts["pixel_" + suffix] += pixel
                if pixel and secondary:
                    processes[truth[tuple(h[k] for k in ids)]] += 1
                    pts.append(math.hypot(float(h["tpx"]), float(h["tpy"])))
        row = dict(counts)
        row["event"] = ev
        row["pixel_process"] = dict(processes)
        row["pixel_secondary_pt"] = np.histogram(pts, ptbins)[0].tolist()
        events.append(row)
    result["runs"][name] = {"metadata": meta, "events": events}
    summary = {k: float(np.mean([e[k] for e in events])) for k in ["ID_primary", "ID_secondary", "pixel_primary", "pixel_secondary"]}
    summary["cpu_s_per_event"] = meta["sequencer_cpu_seconds"] / 3
    summary["failures"] = sum(meta["navigation"]["statistics"]["failures"])
    summary["pixel_process"] = {str(k): float(np.mean([e["pixel_process"].get(str(k), 0) for e in events])) for k in range(1, 7)}
    result["summary"][name] = summary

repeats = json.loads((a.work / "repeated-timings.json").read_text())
result["repeat_timings"] = repeats
for variant, name in [("baseline", "Bounded: softer transport"), ("pruned", "Optimised navigation")]:
    values = [r["cpu_s_per_event"] for r in repeats if r["variant"] == variant]
    result["summary"][name]["cpu_s_per_event"] = float(np.median(values))
    result["summary"][name]["repeat_cpu_range"] = [min(values), max(values)]

# Compare complete particle/sensor crossing multiplicities, without hit cuts.
probe_names = ["probe-cache", "probe-reference025", "probe-helix-refine", "probe-helix-fine-ok", "probe-helix20"]
probes = {}
for n in probe_names:
    with open_csv(a.work / n / "event000000000-hits.csv") as f:
        probes[n] = collections.Counter((r["particle_id_part"], r["geometry_id"]) for r in csv.DictReader(f))
ref = probes["probe-reference025"]
result["probes"] = {}
for n, counter in probes.items():
    result["probes"][n] = {"hits": sum(counter.values()), "missing_crossings_vs_025mm": sum((ref - counter).values()), "extra_crossings_vs_025mm": sum((counter - ref).values()), "missing_unique_particle_sensors": len(ref.keys() - counter.keys()), "extra_unique_particle_sensors": len(counter.keys() - ref.keys()), "failures": sum(json.loads((a.work / n / "metadata.json").read_text())["navigation"]["statistics"]["failures"])}

# Repeated unchanged-physics timings must also preserve the complete output.
result["exact_replays"] = {}
reference_dir = a.work / "pruned-check"
for record in repeats:
    path = a.work / Path(record["output"]).name
    reference_hashes = csv_hashes(reference_dir)
    checks = {name: value == reference_hashes[name] for name, value in csv_hashes(path).items()}
    assert len(checks) == 6 and all(checks.values())
    result["exact_replays"][path.name] = checks
(a.output / "summary.json").write_text(json.dumps(result, indent=2))

labels = ["ACTS main", "Bounded: softer transport", "Optimised navigation", "Helix 0.25 rad (experimental)", "Helix 0.05 rad (experimental)", "Geant4 default, ID only"]
display = ["ACTS main\n300b664a3d", "Soft transport\nbefore optimisation", "Optimised\nnavigation", "Helix 0.25 rad\nexperimental", "Helix 0.05 rad\nexperimental", "Geant4\nID only"]
colors = ["#777777", "#8da0cb", "#1b9e77", "#e6ab02", "#a6761d", "#d95f02"]
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
footer = "3 matched ttbar + PU200 events; 2 T; physical ODD ID; all written hits, no analysis cuts.\nFinite transport thresholds/loop budgets remain. Main CPU: archived 5 events; G4 default ID-only: archived 3 events."
with PdfPages(a.output / "transport_optimisation.pdf") as pdf:
    def save(fig, extra=""):
        fig.text(.04, .025, footer + "\n" + extra, fontsize=7.5)
        fig.tight_layout(rect=(0, .15, 1, .95))
        pdf.savefig(fig)
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    fig.suptitle("Transport optimisation: inclusive occupancy and cost")
    for ax, key, title in [(axes[0], "pixel_secondary", "Secondary pixel hits/event"), (axes[1], "cpu_s_per_event", "Process CPU s/event including CSV")]:
        vals = [result["summary"][n][key] for n in labels]
        ax.bar(range(len(vals)), vals, color=colors)
        ax.set_xticks(range(len(vals)), display, rotation=25, ha="right")
        ax.set_title(title)
        for i, v in enumerate(vals): ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
        ax.set_ylim(0, max(vals) * 1.15)
    save(fig, "Before/after navigation: medians of three sequential 3-event repetitions. Helix: one 3-event timing; accuracy tradeoff, not production default.")
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    fig.suptitle("Inclusive process composition and primary/secondary ID hits")
    bottom = np.zeros(len(labels))
    for code, process in [("5", "Ionisation"), ("2", "Conversion"), ("1", "Decay"), ("4", "Nuclear"), ("6", "Other")]:
        vals = [result["summary"][n]["pixel_process"].get(code, 0) for n in labels]
        axes[0].bar(range(len(labels)), vals, bottom=bottom, label=process)
        bottom += vals
    axes[0].legend(fontsize=8)
    axes[0].set_ylabel("Secondary pixel hits/event")
    for key, offset, color in [("ID_primary", -.18, "#4c78a8"), ("ID_secondary", .18, "#f58518")]:
        axes[1].bar(np.arange(len(labels)) + offset, [result["summary"][n][key] for n in labels], width=.36, label=key, color=color)
    axes[1].legend(fontsize=8)
    for ax in axes: ax.set_xticks(range(len(labels)), display, rotation=25, ha="right")
    save(fig, "Changing the stepper changes random-number consumption; three-event process differences are not precise independent channel gains.")
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    fig.suptitle("Momentum distribution and deterministic crossing check")
    for name, color in zip(labels, colors):
        values = np.mean([e["pixel_secondary_pt"] for e in result["runs"][name]["events"]], axis=0)
        axes[0].stairs(values, range(13), label=name, color=color)
    axes[0].set_xticks(np.arange(12) + .5, ["0–1", "1–5", "5–20", "20–50", "50–100", "100–200", "200–500", "500–1k", "1k–2k", "2k–10k", "10k–100k", "≥100k"], rotation=65, ha="right")
    axes[0].set(xlabel="Hit pT bin [MeV] (all bins included)", ylabel="Secondary pixel hits/event")
    axes[0].legend(fontsize=6)
    probe_display = ["Numerical\n5 mm", "Numerical\n0.25 mm reference", "Helix\n5 mm / 0.25 rad", "Helix\n5 mm / 0.05 rad", "Helix\n20 mm / 0.25 rad"]
    axes[1].bar(range(5), [result["probes"][n]["missing_crossings_vs_025mm"] for n in probe_names])
    axes[1].set_xticks(range(5), probe_display, rotation=25, ha="right")
    axes[1].set_ylabel("Missing particle/sensor crossings vs fine numerical probe")
    save(fig, "1440 stable charged probes; both charges, displaced/inward/looping tracks. Fine numerical reference is a convergence diagnostic, not G4 ground truth.")
print(json.dumps({k: {x: v[x] for x in ["pixel_secondary", "ID_secondary", "cpu_s_per_event"]} for k, v in result["summary"].items()}, indent=2))
