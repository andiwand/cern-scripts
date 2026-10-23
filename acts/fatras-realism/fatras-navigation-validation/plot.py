#!/usr/bin/env python3
"""Plot navigation/transport ablations with matched-event differences and CPU."""

import argparse, json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--results", type=Path, required=True)
p.add_argument("--reference", type=Path, required=True)
a = p.parse_args()
r = a.results
ref = json.loads(a.reference.read_text())
previous = ref["runs"]["Current Fatras"]["events"]
g4 = ref["runs"]["Geant4"]["events"]
labels = {
    "fatras-nav-native-budget": "Standard; 5k steps",
    "fatras-nav-native-fullturn": "Standard; full turn",
    "fatras-nav-native-lowcuts": "Standard; full turn + low cuts",
    "fatras-nav-tryall20": "TryAll 20 mm; half turn",
    "fatras-nav-tryall20-fullturn": "TryAll 20 mm; full turn",
    "fatras-nav-tryall20-lowcuts": "TryAll 20 mm; full turn + low cuts",
    "fatras-nav-tryall10-fullturn": "TryAll 10 mm; full turn",
    "fatras-nav-native-fourturn": "Standard; 4 turns + low cuts",
    "fatras-nav-tryall10-fourturn": "TryAll 10 mm; 4 turns + low cuts",
}
runs = {
    key: json.loads((r / (key + ".json")).read_text())
    for key in labels
    if (r / (key + ".json")).exists()
}


def total(e):
    return sum(v["hits"] for v in e["process"].values())


def mean(x):
    return float(np.mean(x))


def sem(x):
    return float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0


plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42})
page = 0
with PdfPages(r / "navigation_diagnostics_with_cuts.pdf") as pdf:

    def save(fig, note):
        global page
        page += 1
        fig.text(0.04, 0.025, note, fontsize=8.5, va="bottom")
        fig.tight_layout(rect=(0, 0.12, 1, 0.94))
        pdf.savefig(fig)
        fig.savefig(r / f"navigation_page{page}.png", dpi=115)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.axis("off")
    fig.suptitle("Low-momentum transport hypothesis — matched ODD events")
    rows = [
        ["ACTS main", "20", "3,803", "—", "0.820", "2"],
        ["Current Fatras, before test", "20", "15,776", "—", "1.124", "1"],
        ["Geant4, strictly ID only", "20", "18,402", "—", "39.701", "—"],
    ]
    for key, d in runs.items():
        s = d["summary"]
        gain = s["paired_secondary_gain"]
        fail = sum(
            d["metadata"]["charged_navigation_experiment"]["statistics"]["failures"]
        )
        rows.append(
            [
                labels[key],
                str(len(d["events"])),
                f"{s['secondary_hits']['mean']:,.1f}",
                (
                    f"{gain['mean']:+.1f} ±{gain['sem']:.1f}"
                    if gain["sem"] is not None
                    else f"{gain['mean']:+.1f}"
                ),
                f"{s['cpu_s_per_event']:.3f}",
                str(fail),
            ]
        )
    t = ax.table(
        cellText=rows,
        colLabels=[
            "Configuration",
            "Events",
            "Secondary hits/event",
            "Paired gain",
            "CPU s/event",
            "Failed particles",
        ],
        loc="center",
        cellLoc="center",
        colWidths=[0.34, 0.06, 0.18, 0.17, 0.12, 0.13],
    )
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    t.scale(1, 2)
    save(
        fig,
        "20-event physics sample; TryAll subsets use identical event IDs and their own matched baseline for gains. Error: paired event SEM.\nCPU includes CSV output; one worker, sequential measurements. Raw means across different sample sizes are not directly comparable.\nTryAll is selected at charged-particle birth for pT < 0.5 GeV; neutrals unchanged. Same physics and diagnostic hadronic library throughout.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Where do extra hits come from?")
    xs = np.arange(6)
    ptlabels = ["50–100", "100–200", "200–500", "500–1000", "1000–2000", ">2000"]
    for key, d in runs.items():
        rows = d["events"]
        n = len(rows)
        diff = np.array(
            [
                np.sum([v["hit_pt_bins"] for v in e["process"].values()], axis=0)
                - np.sum([v["hit_pt_bins"] for v in b["process"].values()], axis=0)
                for e, b in zip(rows, previous)
            ]
        )
        axes[0].plot(xs, diff.mean(axis=0), marker=".", label=labels[key])
        proc = [
            d["summary"]["process"][x]["paired_gain"]["mean"]
            for x in ["conversion", "decay", "nuclear"]
        ]
        axes[1].plot(range(3), proc, marker=".", label=labels[key])
    axes[0].set_xticks(xs, ptlabels, rotation=25)
    axes[0].set_xlabel("Hit-entry pT [MeV]")
    axes[0].set_ylabel("Paired hit gain/event")
    axes[1].set_xticks(range(3), ["Conversion", "Decay", "Nuclear"])
    axes[1].set_ylabel("Paired hit gain/event")
    for ax in axes:
        ax.axhline(0, color=".4", lw=0.8)
    axes[0].legend(fontsize=7)
    save(
        fig,
        "Common hit-entry p ≥ 100 MeV, pT ≥ 50 MeV; pixels 16–18. Process denotes immediate creation, not full cascade origin.\nLow cuts change charged transport only: p ≥ 20 MeV, pT ≥ 5 MeV. Neutral acceptance and hadronic table domains are unchanged.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Coverage and cost: more hits must mean useful sensor crossings")
    for i, (key, d) in enumerate(runs.items()):
        rows = d["events"]
        g = [
            sum(
                e["process"][p]["particles_at_least_3_sensors"]
                - b["process"][p]["particles_at_least_3_sensors"]
                for p in e["process"]
            )
            for e, b in zip(rows, previous)
        ]
        repeats = mean(
            [
                sum(v["repeated_sensor_hits"] for v in e["process"].values())
                for e in rows
            ]
        )
        axes[0].errorbar(i, mean(g), yerr=sem(g), fmt="o", capsize=3)
        axes[0].text(
            i, mean(g), f"  repeats {repeats:.1f}", rotation=90, fontsize=7, va="bottom"
        )
        s = d["summary"]
        axes[1].errorbar(
            s["cpu_s_per_event"],
            s["paired_secondary_gain"]["mean"],
            yerr=s["paired_secondary_gain"]["sem"] or 0,
            fmt="o",
            label=labels[key],
        )
    axes[0].set_xticks(
        range(len(runs)), [labels[k] for k in runs], rotation=45, ha="right"
    )
    axes[0].set_ylabel("Paired gain: particles crossing ≥3 sensors/event")
    axes[0].axhline(0, color=".4", lw=0.8)
    axes[1].set_xlabel("Event-loop CPU [s/event]")
    axes[1].set_ylabel("Paired secondary-hit gain/event")
    axes[1].set_xscale("log")
    axes[1].axvline(39.701, color=".5", ls="--", label="Geant4 CPU (20 events)")
    axes[1].legend(fontsize=7)
    save(
        fig,
        "Unique sensors are counted per particle/event; this is not reconstructed tracking efficiency. Repeated sensor hits may be physical.\nChanging navigation changes random histories and cascades; all gains are measured against the same inputs, not identical random trajectories.",
    )
    f = r / "reference-cuts.json"
    if f.exists():
        q = json.loads(f.read_text())["events"]
        totalhits = mean([e["accepted_secondary_hits"] for e in q])
        carrier = mean([e["carrier_born_below_cuts"] for e in q])
        ancestor = mean([e["any_charged_ancestor_born_below_cuts"] for e in q])
        fig, ax = plt.subplots(figsize=(11.7, 8.3))
        fig.suptitle(
            "Geant4 ancestry check: which accepted hits are exposed to birth cuts?"
        )
        ax.bar(
            [
                "All accepted secondary hits",
                "Carrier born below cuts",
                "Carrier or charged ancestor\nborn below cuts",
            ],
            [totalhits, carrier, ancestor],
            color=[".4", "#4c78a8", "#f28e2b"],
        )
        for i, y in enumerate([totalhits, carrier, ancestor]):
            ax.text(i, y + 200, f"{y:,.1f} ({100*y/totalhits:.1f}%)", ha="center")
        ax.set_ylabel("Reference hits/event")
        ax.set_ylim(0, totalhits * 1.15)
        save(
            fig,
            "Birth cuts: charged p < 100 MeV OR pT < 50 MeV. Common hit-entry cuts remain p ≥ 100 MeV and pT ≥ 50 MeV.\nUses recorded birth momentum, not subsequent energy loss or a later crossing of the transport cut. Exposure is not a recoverable-gain prediction.\nThis distinguishes low hit momentum (<500 MeV, where 95% of the gap lies) from particles initially rejected by the configured cuts.",
        )
    f = r / "inclusive.json"
    if f.exists():
        q = json.loads(f.read_text())
        keys = ["accepted", "below_pt_only", "below_p_only", "below_both"]
        names = ["Accepted", "pT <50 MeV only", "p <100 MeV only", "Below both cuts"]
        fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
        fig.suptitle("Accepted tracks versus inclusive soft occupancy")
        for i, (label, color) in enumerate(
            [("Current Fatras", "#4c78a8"), ("Geant4", "#f28e2b")]
        ):
            ys = [mean([e[k] for e in q["runs"][label]]) for k in keys]
            axes[0].bar(
                np.arange(4) + (i - 0.5) * 0.35,
                ys,
                width=0.35,
                label=label,
                color=color,
            )
            bins = np.mean([e["pt_bins"] for e in q["runs"][label]], axis=0)
            axes[1].plot(range(8), bins, marker="o", label=label, color=color)
        axes[0].set_xticks(range(4), names, rotation=30, ha="right")
        axes[0].set_ylabel("Secondary pixel hits/event")
        axes[0].legend()
        axes[1].set_xticks(
            range(8),
            [
                "<5",
                "5–20",
                "20–50",
                "50–100",
                "100–200",
                "200–500",
                "500–1000",
                ">1000",
            ],
            rotation=35,
        )
        axes[1].set_xlabel("Hit-entry pT [MeV], no p cut")
        axes[1].set_ylabel("Secondary pixel hits/event")
        axes[1].legend()
        save(
            fig,
            "20 matched events, strict ID-only Geant4. These are recorded sensitive crossings, not digitised clusters or reconstructed tracks.\nThe accepted-track metric excludes low-momentum occupancy by design; its deficit and the inclusive deficit must be reported separately.",
        )
    f = r / "probe.json"
    if f.exists():
        q = json.loads(f.read_text())
        fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
        fig.suptitle("Transport-only muons: navigation and step-size sensitivity")
        for label, d in q["runs"].items():
            pts = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
            rows = list(d["particles"].values())
            hits = [
                sum(v["hits"] for v in rows if abs(v["pt_GeV"] - pt) < 1e-8)
                for pt in pts
            ]
            sensors = [
                sum(len(v["sensors"]) for v in rows if abs(v["pt_GeV"] - pt) < 1e-8)
                for pt in pts
            ]
            short = label.replace("fatras-nav-probe-v2-", "")
            axes[0].plot(pts, hits, marker="o", label=short)
            axes[1].plot(pts, sensors, marker="o", label=short)
        for ax in axes:
            ax.set_xscale("log")
            ax.set_xlabel("Muon pT [GeV]")
            ax.legend()
        axes[0].set_ylabel("Inclusive pixel crossings")
        axes[1].set_ylabel("Unique particle–sensor pairs")
        save(
            fig,
            "432 stable muons, eta 0/1/2, eight phi directions, birth radii 0/40/120 mm; no material interactions or decays.\nFour-turn initial path budget, 5000-step cap, charged cuts 1 MeV. TryAll for every probe particle.\nThis isolates navigator behavior; no Geant4 ground truth. Inclusive crossings include repeated visits to a sensor.",
        )
    f = r / "inclusive.json"
    if f.exists():
        q = json.loads(f.read_text())
        rows = q["runs"]["Geant4"]
        if "soft_process" in rows[0]:
            names = [
                "Undefined",
                "Decay",
                "Conversion",
                "Bremsstrahlung",
                "Nuclear",
                "Ionisation",
                "Other",
            ]
            values = [
                mean([e["soft_process"].get(str(i), 0) for e in rows]) for i in range(7)
            ]
            fig, ax = plt.subplots(figsize=(11.7, 8.3))
            fig.suptitle("What produces Geant4 hits below the common momentum cuts?")
            ax.bar(range(7), values, color="#f28e2b")
            ax.set_xticks(range(7), names, rotation=25)
            ax.set_ylabel("Soft secondary pixel hits/event")
            for i, v in enumerate(values):
                ax.text(i, v + 100, f"{v:,.0f}", ha="center")
            save(
                fig,
                "20 strict-ID events. Soft means hit-entry p <100 MeV OR pT <50 MeV. Immediate creation process, not cascade origin.\nLowering cuts and fixing navigation cannot create missing processes such as explicit ionisation electrons.\nInclusive occupancy therefore tests both soft-particle production and transport; it is not solely a navigation efficiency.",
            )
        key = "fatras-nav-tryall10-fourturn"
        if key in q["runs"]:
            trial = q["runs"][key]
            n = len(trial)
            fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
            fig.suptitle(f"Longer TryAll transport — {n} matched events")
            labels2 = [
                "Current Fatras",
                "Standard, four turns\nand low cuts",
                "TryAll, four turns\nand low cuts",
                "Geant4 ID only",
            ]
            series = [
                q["runs"]["Current Fatras"][:n],
                q["runs"]["fatras-nav-native-fourturn"][:n],
                trial,
                q["runs"]["Geant4"][:n],
            ]
            for ax, metric, title in zip(
                axes,
                ["accepted", "all"],
                ["Accepted secondary hits", "Inclusive secondary hits"],
            ):
                values = [mean([v[metric] for v in x]) for x in series]
                ax.bar(range(4), values, color=[".5", "#72b7b2", "#4c78a8", "#f28e2b"])
                ax.set_xticks(range(4), labels2, rotation=35, ha="right")
                ax.set_ylabel("Hits/event")
                ax.set_title(title)
                for i, v in enumerate(values):
                    ax.text(i, v + 100, f"{v:,.0f}", ha="center")
            save(
                fig,
                "Identical first three events in all four bars. TryAll far limit and maximum step 10 mm; charged p/pT cuts 20/5 MeV.\nTryAll versus standard with the same settings isolates the navigator change statistically, with changed random histories.\nThree events are a diagnostic, not a production calibration. The four-turn setting is a path budget, not unlimited transport.",
            )
