#!/usr/bin/env python3
"""Summarize matched CPU timing and separately measured algorithm elapsed time."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser(description=__doc__)
for name in ["main", "changed", "geant4", "output"]:
    p.add_argument(f"--{name}", type=Path, required=True)
p.add_argument("--host-label", required=True)
a = p.parse_args()
keys = ["main", "changed", "geant4"]
labels = ["ACTS main", "Current Fatras", "Geant4"]
result = {"host": a.host_label, "runs": {}}
for key in keys:
    folder = getattr(a, key)
    meta = json.loads((folder / "metadata.json").read_text())
    assert meta["mode"] == ("fatras-main" if key == "main" else key)
    assert not meta["acts_worktree_dirty"] and meta["num_threads"] == 1
    if key == "geant4":
        assert (
            meta["geant4_world"]["world_solid"] == "G4Tubs"
        ), "Require the strictly ID-bounded reference"
    with (folder / "timing.csv").open() as f:
        algorithms = [
            r for r in csv.DictReader(f) if r["identifier"].startswith("Algorithm:")
        ]
    assert len(algorithms) == 1
    n = meta["events"]
    result["runs"][key] = {
        "directory": str(folder),
        "metadata": meta,
        "event_loop_cpu_s_per_event": meta["sequencer_cpu_seconds"] / n,
        "total_cpu_s_per_event": meta["process_cpu_seconds"] / n,
        "simulation_wall_s_per_event": float(algorithms[0]["time_perevent_s"]),
    }
for field in [
    "events",
    "seed",
    "input",
    "odd_revision",
    "material_map_sha256",
    "world_bounds",
    "field_T",
]:
    assert (
        len({json.dumps(r["metadata"][field]) for r in result["runs"].values()}) == 1
    ), field
a.output.mkdir(parents=True, exist_ok=True)
(a.output / "cpu-comparison.json").write_text(json.dumps(result, indent=2) + "\n")
plt.rcParams.update({"font.size": 11, "pdf.fonttype": 42})
fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
fig.suptitle("ODD simulation cost: main, current Fatras and Geant4", fontsize=17)
rows = list(result["runs"].values())
loop = [r["event_loop_cpu_s_per_event"] for r in rows]
setup = [r["total_cpu_s_per_event"] - r["event_loop_cpu_s_per_event"] for r in rows]
axes[0].bar(labels, loop, label="Event loop, including CSV", color="#0072b2")
axes[0].bar(
    labels, setup, bottom=loop, label="Setup amortized over 20 events", color="#e69f00"
)
axes[0].set_title("Process CPU: user + system")
axes[0].set_ylabel("CPU seconds / event")
axes[0].legend(loc="upper left", fontsize=9)
wall = [r["simulation_wall_s_per_event"] for r in rows]
axes[1].bar(labels, wall, color=["#999999", "#009e73", "#333333"])
axes[1].set_title("Simulation algorithm elapsed time")
axes[1].set_ylabel("Elapsed seconds / event (CSV excluded)")
for ax, values in zip(axes, [[r["total_cpu_s_per_event"] for r in rows], wall]):
    ax.set_yscale("log")
    ax.set_ylim(min(values) * 0.6, max(values) * 3)
    ax.grid(axis="y", alpha=0.2)
    for i, v in enumerate(values):
        ax.text(i, v * 1.12, f"{v:.3f}", ha="center")
fig.text(
    0.04,
    0.035,
    a.host_label + "; 20 matched ttbar + PU200 events; 2 T, ODD tracker.\n"
    "One sequential run per variant; one worker; standard hit/truth CSV writers, no physics observers.\n"
    "CPU includes all process threads. Algorithm elapsed time is not a separate CPU measurement.\n"
    "Both Fatras runs use pMin = 100 MeV and the same corrected map; main has no pT transport cut.",
    fontsize=10,
)
fig.tight_layout(rect=[0, 0.15, 1, 0.94])
fig.savefig(a.output / "cpu_comparison.pdf")
fig.savefig(a.output / "cpu_comparison.png", dpi=110)
plt.close(fig)
print(
    json.dumps(
        {
            k: {f: v for f, v in r.items() if f != "metadata"}
            for k, r in result["runs"].items()
        },
        indent=2,
    )
)
