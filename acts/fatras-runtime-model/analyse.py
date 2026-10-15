#!/usr/bin/env python3
"""Inclusive comparison with archived, input-hash-matched main and ID Geant4."""

import argparse, csv, collections, json, math
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def open_csv(path):
    import gzip

    return (
        path.open() if path.exists() else gzip.open(path.with_suffix(".csv.gz"), "rt")
    )


p = argparse.ArgumentParser()
p.add_argument("--results", type=Path, required=True)
p.add_argument("--reference", type=Path, required=True)
a = p.parse_args()
root = a.results
reference = json.loads(a.reference.read_text())
BAR = ["particle_id_" + x for x in ["pv", "sv", "part", "gen", "subpart"]]
PT = [0, 0.001, 0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 10, 100, np.inf]
TIME = [0, 1, 10, 100, 1000, 10000, 1e6, np.inf]
labels = [
    "ACTS main (300b664a3d)",
    "Fatras: event replay",
    "Fatras: on-demand G4",
    "Geant4: ID only",
]
colors = ["#777777", "#4c78a8", "#279b6c", "#f28e2b"]
runs = {
    labels[0]: reference["runs"]["ACTS main"],
    labels[3]: reference["runs"]["Geant4 default, ID only"],
}
for name, label in [("changed", labels[1]), ("live", labels[2])]:
    folder = root / name
    meta = json.loads((folder / "metadata.json").read_text())
    rows = []
    assert (
        meta["analysis_hit_p_min_GeV"] is None
        and meta["analysis_hit_pt_min_GeV"] is None
    )
    for event in range(meta["events"]):
        file = f"event{event:09d}"
        expected = runs[labels[0]]["metadata"]["input_selection"]["sha256"][
            file + "-particles.csv"
        ]
        assert meta["input_selection"]["sha256"][file + "-particles.csv"] == expected
        with open_csv(folder / (file + "-particles_simulated.csv")) as f:
            truth = {tuple(r[x] for x in BAR): r for r in csv.DictReader(f)}
        with open_csv(folder / (file + "-hits.csv")) as f:
            hits = list(csv.DictReader(f))
        row = {
            "event": event,
            "ID_primary": 0,
            "ID_secondary": 0,
            "pixel_primary": 0,
            "pixel_secondary": 0,
        }
        hist = collections.defaultdict(list)
        counts = collections.defaultdict(collections.Counter)
        for h in hits:
            assert (
                math.hypot(float(h["tx"]), float(h["ty"])) <= 1202.001
                and abs(float(h["tz"])) <= 4002.001
            )
            v = int(h["geometry_id"]) >> 56
            pixel = v in [16, 17, 18]
            secondary = int(h["particle_id_gen"]) > 0
            suffix = "secondary" if secondary else "primary"
            row["ID_" + suffix] += 1
            row["pixel_" + suffix] += pixel
            if not secondary:
                continue
            t = truth[tuple(h[x] for x in BAR)]
            pt = math.hypot(float(h["tpx"]), float(h["tpy"]))
            mom = math.hypot(pt, float(h["tpz"]))
            hist["ID_secondary_pt"].append(pt)
            hist["ID_secondary_p"].append(mom)
            hist["ID_secondary_time"].append(float(h["tt"]) / 299.792458)
            counts["volume_secondary"][str(v)] += 1
            for region in ["ID"] + (["pixel"] if pixel else []):
                counts[region + "_process"][t["process"]] += 1
                counts[region + "_pdg"][t["particle_type"]] += 1
            if pixel:
                hist["pixel_secondary_pt"].append(pt)
        for k, v in hist.items():
            row[k] = np.histogram(v, TIME if k.endswith("_time") else PT)[0].tolist()
        for k, v in counts.items():
            row[k] = dict(v)
        for region in ["ID", "pixel"]:
            assert sum(row[region + "_process"].values()) == row[region + "_secondary"]
            assert sum(row[region + "_pdg"].values()) == row[region + "_secondary"]
            assert sum(row[region + "_secondary_pt"]) == row[region + "_secondary"]
        rows.append(row)
    runs[label] = {"metadata": meta, "events": rows, "folder": str(folder)}
summary = {}
for label in labels:
    v = runs[label]
    n = len(v["events"])
    summary[label] = {}
    for k in ["ID_primary", "ID_secondary", "pixel_primary", "pixel_secondary"]:
        nums = [e[k] for e in v["events"]]
        summary[label][k] = {
            "mean": float(np.mean(nums)),
            "sem": float(np.std(nums, ddof=1) / np.sqrt(n)),
        }
    summary[label].update(
        event_cpu_s=v["metadata"]["sequencer_cpu_seconds"] / n,
        setup_cpu_s=v["metadata"]["setup_cpu_seconds"],
        rss_MiB=v["metadata"]["max_rss_MiB"],
    )
# Archived reference is only reused after verifying hashes for every event.
replay_same = all(
    runs[labels[1]]["events"][i][k]
    == reference["runs"]["Changed Fatras"]["events"][i][k]
    for i in range(5)
    for k in [
        "ID_primary",
        "ID_secondary",
        "pixel_primary",
        "pixel_secondary",
        "ID_secondary_pt",
        "pixel_secondary_pt",
        "ID_process",
        "pixel_process",
    ]
)
paired = {}
for key in ["ID_secondary", "pixel_secondary"]:
    diff = np.array(
        [
            x[key] - y[key]
            for x, y in zip(runs[labels[2]]["events"], runs[labels[1]]["events"])
        ]
    )
    paired[key] = {
        "mean_difference": float(diff.mean()),
        "paired_sem": float(diff.std(ddof=1) / np.sqrt(len(diff))),
    }
result = {
    "runs": runs,
    "summary": summary,
    "paired_live_minus_replay": paired,
    "replay_reproduces_archived_hits": replay_same,
    "scope": "All recorded sensitive hits, no analysis or input momentum/time cuts. Archived main and Geant4 reference; newly timed replay/live runs. Inputs reproduced byte-for-byte. Five events only.",
}
(root / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        {
            "summary": summary,
            "paired": paired,
            "replay_reproduces_archived_hits": replay_same,
        },
        indent=2,
    )
)
plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42})
footer = "5 matched ttbar + fixed PU200 events, seed 42, 2 T. No input or analysis momentum cuts.\nGeant4 FTFP_BERT defaults, physical ID world r=1202 mm, |z|=4002 mm; no extra time kill."
with PdfPages(root / "inclusive_file_free.pdf") as pdf:

    def save(fig, extra=""):
        fig.text(0.04, 0.025, footer + "\n" + extra, fontsize=8)
        fig.tight_layout(rect=(0, 0.15, 1, 0.94))
        pdf.savefig(fig)
        plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Removing the event library: inclusive secondary hits")
    for ax, key, title in zip(
        axs, ["ID_secondary", "pixel_secondary"], ["All ID sensors", "Pixel sensors"]
    ):
        vals = [summary[l][key]["mean"] for l in labels]
        err = [summary[l][key]["sem"] for l in labels]
        ax.bar(range(4), vals, yerr=err, color=colors, capsize=3)
        ax.set_xticks(range(4), labels, rotation=25, ha="right")
        ax.set_ylabel("Secondary hits/event")
        ax.set_title(title)
        for i, x in enumerate(vals):
            ax.text(i, x + max(vals) * 0.06, f"{x:,.0f}", ha="center")
        ax.set_ylim(0, max(vals) * 1.3)
    save(
        fig,
        "Bars are absolute counts. Error bars: event SEM. This diagnostic sample does not establish reconstruction closure.",
    )
    fig, axs = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Inclusive secondary-hit transverse momentum")
    for ax, key, title in zip(
        axs,
        ["ID_secondary_pt", "pixel_secondary_pt"],
        ["All ID sensors", "Pixel sensors"],
    ):
        for label, color in zip(labels, colors):
            values = np.mean([e[key] for e in runs[label]["events"]], axis=0)
            ax.stairs(values, np.arange(13), label=label, color=color)
        ax.set_yscale("log")
        ax.set_xticks(
            np.arange(12) + 0.5,
            [
                "0–1",
                "1–5",
                "5–20",
                "20–50",
                "50–100",
                "100–200",
                "200–500",
                "500–1k",
                "1k–2k",
                "2k–10k",
                "10k–100k",
                ">100k",
            ],
            rotation=60,
        )
        ax.set_xlabel("pT at hit [MeV/c], bin interval")
        ax.set_ylabel("Secondary hits/event/bin")
        ax.set_title(title)
        ax.legend(fontsize=8)
    save(
        fig,
        "Includes under-threshold and overflow bins; no normalization to the reference.",
    )
    fig, axs = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Secondary hits by generating process")
    processes = [
        ("3", "Bremsstrahlung"),
        ("2", "Conversion"),
        ("1", "Decay"),
        ("4", "Nuclear"),
        ("5", "Ionisation"),
        ("6", "Other"),
        ("0", "Undefined"),
    ]
    for ax, region in zip(axs, ["ID", "pixel"]):
        keys = sorted(
            {
                k
                for l in labels
                for e in runs[l]["events"]
                for k in e[region + "_process"]
            }
        )
        mapping = dict(processes)
        bottom = np.zeros(4)
        for k in keys:
            values = np.array(
                [
                    np.mean(
                        [e[region + "_process"].get(k, 0) for e in runs[l]["events"]]
                    )
                    for l in labels
                ]
            )
            ax.bar(
                range(4), values, bottom=bottom, label=mapping.get(k, "Process " + k)
            )
            bottom += values
        ax.set_xticks(range(4), labels, rotation=25, ha="right")
        ax.set_title(region + " sensors")
        ax.set_ylabel("Secondary hits/event")
        ax.legend(fontsize=8)
    save(
        fig,
        "Generating-process categories follow the recorded truth; descendants can belong to later EM or decay processes.",
    )
    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.axis("off")
    fig.suptitle("CPU, memory and custom runtime payload")
    rows = []
    for i, l in enumerate(labels):
        s = summary[l]
        rows.append(
            [
                l,
                f"{s['event_cpu_s']:.3f}",
                f"{s['setup_cpu_s']:.2f}",
                f"{s['rss_MiB']:.0f}",
                ["0", "561 MiB", "0", "0"][i],
                ["14 Oct", "15 Oct", "15 Oct", "14 Oct"][i],
            ]
        )
    tab = ax.table(
        cellText=rows,
        colLabels=[
            "Simulation",
            "CPU s/event",
            "Setup CPU s/job",
            "Peak RSS MiB",
            "Custom physics file",
            "Measured",
        ],
        cellLoc="center",
        loc="center",
        colWidths=[0.29, 0.14, 0.16, 0.14, 0.14, 0.1],
    )
    tab.auto_set_font_size(False)
    tab.set_fontsize(9)
    tab.scale(1, 2.1)
    ax.text(
        0.02,
        0.2,
        "On-demand Fatras still requires Geant4 and its standard installed datasets.\nAll transport stays in Fatras. First backend uses a Si reference target and one calling thread.\nCPU includes CSV I/O; timings are sequential snapshots, not a throughput study.",
        transform=ax.transAxes,
    )
    save(
        fig,
        "ACTS-main and Geant4 CPU are archived measurements on these identical inputs; new Fatras pair measured sequentially today.",
    )
