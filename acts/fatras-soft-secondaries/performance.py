"""Summarise archived soft-secondary transport timings; no simulation rerun."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
labels = ["<5", "5–20", "20–50", "50–200", "≥200"]
summary = {"measurement_date": "2026-10-15", "events": 3, "cases": {}}
for name in ["standard-final", "bounded-all", "bounded-soft"]:
    meta_path = a.input / name / "metadata.json"
    timing_path = a.input / name / "timing.csv"
    meta = json.loads(meta_path.read_text())
    with timing_path.open() as f:
        timing = {r["identifier"]: float(r["time_perevent_s"]) for r in csv.DictReader(f)}
    result = {
        "sequencer_cpu_s_per_event": meta["sequencer_cpu_seconds"] / 3,
        "algorithm_elapsed_s_per_event": timing["Algorithm:RuntimeFatras"],
        "io_elapsed_s_per_event": sum(v for k, v in timing.items() if k.startswith(("Reader:", "Writer:"))),
        "input_sha256": {str(x): hashlib.sha256(x.read_bytes()).hexdigest() for x in [meta_path, timing_path]},
    }
    if "navigation" in meta:
        stats = meta["navigation"]["statistics"]
        result["birth_pt_bins_MeV"] = []
        for i, label in enumerate(labels):
            calls, steps = stats["calls"][i], stats["steps"][i]
            result["birth_pt_bins_MeV"].append({
                "bin": label,
                "calls_per_event": calls / 3,
                "transport_elapsed_s_per_event": stats["transport_seconds"][i] / 3,
                "steps_per_event": steps / 3,
                "steps_per_call": steps / calls if calls else None,
                "path_mm_per_step": stats["path_mm"][i] / steps if steps else None,
                "failures": stats["failures"][i],
            })
        result["queries_per_event"] = stats["queries"] / 3
        result["selected_candidates_per_event"] = stats["tested"] / 3
    summary["cases"][name] = result

a.output.mkdir(parents=True, exist_ok=True)
(a.output / "performance.json").write_text(json.dumps(summary, indent=2) + "\n")
fig, axes = plt.subplots(1, 2, figsize=(11.7, 6))
for name, label in [("bounded-all", "p≥20, pT≥5 MeV"), ("bounded-soft", "p≥0.2, pT≥0.05 MeV")]:
    rows = summary["cases"][name]["birth_pt_bins_MeV"]
    axes[0].plot(labels, [r["transport_elapsed_s_per_event"] for r in rows], "o-", label=label)
axes[0].set(xlabel="Birth pT [MeV]", ylabel="Charged propagation elapsed time [s/event]", title="Where charged transport spends time")
axes[0].legend(fontsize=8)
cases = list(summary["cases"].values())
sim = [c["algorithm_elapsed_s_per_event"] for c in cases]
io = [c["io_elapsed_s_per_event"] for c in cases]
axes[1].bar(range(3), sim, label="Simulation")
axes[1].bar(range(3), io, bottom=sim, label="CSV input/output")
axes[1].axhline(1, color="black", linestyle="--", linewidth=1, label="1 s/event aspiration")
axes[1].set_xticks(range(3), ["Standard\np100/pT50", "Bounded\np20/pT5", "Bounded softer\np0.2/pT0.05"], fontsize=8)
axes[1].set(ylabel="Algorithm + I/O elapsed time [s/event]", title="Measured components (different transport cuts)")
axes[1].legend(fontsize=8)
for ax in axes:
    ax.grid(axis="y", alpha=.25)
fig.suptitle("Fatras CPU diagnosis · ttbar + PU200 · ODD inner detector · 2 T")
fig.text(.05, .025, "Archived 15 Oct 2026: three events, one worker, one timing/configuration. No new run.\nBirth-pT attribution includes physics inside propagation; it is not a function-level profile.\nCuts shown are transport settings, not analysis cuts. Five failed propagations in softer run; failed steps/path are excluded.", fontsize=8)
fig.tight_layout(rect=(0, .13, 1, .94))
fig.savefig(a.output / "transport_performance.pdf")
