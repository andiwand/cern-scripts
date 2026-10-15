"""Inclusive occupancy and cost attribution for bounded-search feasibility."""

import argparse, csv, json, math, collections, gzip
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser()
p.add_argument("--work", type=Path, required=True)
p.add_argument("--reference", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
records = json.loads((a.work / "lowp-collisions.json").read_text())
reference = json.loads(a.reference.read_text())
bar = ["particle_id_" + v for v in ["pv", "sv", "part", "gen", "subpart"]]
bins = [0, 0.001, 0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 10, 100, np.inf]


def open_csv(path):
    return (
        path.open() if path.exists() else gzip.open(path.with_suffix(".csv.gz"), "rt")
    )


runs = {}
for d in records:
    folder = a.work / Path(d["command"][d["command"].index("--output") + 1]).name
    events = []
    for ev in range(d["events"]):
        stem = f"event{ev:09d}"
        with open_csv(folder / (stem + "-particles_simulated.csv")) as f:
            truth = {tuple(r[k] for k in bar): r for r in csv.DictReader(f)}
        count = collections.Counter()
        pt = []
        proc = collections.Counter()
        pdg = collections.Counter()
        with open_csv(folder / (stem + "-hits.csv")) as f:
            for h in csv.DictReader(f):
                assert (
                    math.hypot(float(h["tx"]), float(h["ty"])) <= 1202.001
                    and abs(float(h["tz"])) <= 4002.001
                )
                pix = int(h["geometry_id"]) >> 56 in [16, 17, 18]
                sec = int(h["particle_id_gen"]) > 0
                suffix = "secondary" if sec else "primary"
                count["ID_" + suffix] += 1
                count["pixel_" + suffix] += pix
                if sec and pix:
                    pt.append(math.hypot(float(h["tpx"]), float(h["tpy"])))
                    t = truth[tuple(h[k] for k in bar)]
                    proc[t["process"]] += 1
                    pdg[t["particle_type"]] += 1
        row = dict(count)
        row["pixel_secondary_pt"] = np.histogram(pt, bins)[0].tolist()
        row["pixel_process"] = dict(proc)
        row["pixel_pdg"] = dict(pdg)
        row["event"] = ev
        events.append(row)
    runs[d["name"]] = {"metadata": d, "events": events}
for name in ["ACTS main", "Geant4 default, ID only"]:
    runs[name] = {
        "metadata": reference["runs"][name]["metadata"],
        "events": reference["runs"][name]["events"][:3],
    }
summary = {}
for name, run in runs.items():
    events = run["events"]
    d = run["metadata"]
    row = {
        key: float(np.mean([e[key] for e in events]))
        for key in ["ID_primary", "ID_secondary", "pixel_primary", "pixel_secondary"]
    }
    row["events"] = len(events)
    row["cpu_s_per_event"] = d["sequencer_cpu_seconds"] / d["events"]
    row["failures"] = (
        sum(d["navigation"]["statistics"]["failures"]) if "navigation" in d else None
    )
    summary[name] = row
result = {
    "runs": runs,
    "summary": summary,
    "scope": "No analysis momentum/time cuts; 3 matched generator events, 2 T, ID only. TryAll exact-output check uses event 0 only. Main/G4 reference archived on 14 October; reference CPU covers five events. Low-momentum settings: p>=20 MeV,pT>=5 MeV; four-turn budget; 50000-step cap for final bounded variants (5000 in initial diagnostic). Not converged transport.",
}
(a.output / "summary.json").write_text(json.dumps(result, indent=2))
print(json.dumps(summary, indent=2))
plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42})
labels = [
    "ACTS main",
    "standard-default",
    "standard-low",
    "bounded5-50k",
    "bounded2p5-50k",
    "Geant4 default, ID only",
]
display = [
    "ACTS main\n300b664a3d",
    "Fatras\ndefault transport",
    "Standard nav\nlower thresholds",
    "Bounded search\n5 mm",
    "Bounded search\n2.5 mm",
    "Geant4\nID only",
]
colors = ["#777777", "#279b6c", "#76b7b2", "#4c78a8", "#b279a2", "#f28e2b"]
footer = "3 matched ttbar + fixed PU200 events; 2 T; no input/hit analysis momentum or time cuts.\nG4 default FTFP_BERT, physical ID r=1202 mm, |z|=4002 mm; no extra global time kill."
with PdfPages(a.output / "low_momentum_feasibility.pdf") as pdf:

    def save(fig, note=""):
        fig.text(0.04, 0.025, footer + "\n" + note, fontsize=8)
        fig.tight_layout(rect=(0, 0.15, 1, 0.94))
        pdf.savefig(fig)
        plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle("Inclusive secondary occupancy: bounded-search feasibility")
    for ax, key, title in zip(
        axs, ["ID_secondary", "pixel_secondary"], ["All ID sensors", "Pixel sensors"]
    ):
        vals = [summary[k][key] for k in labels]
        err = [
            np.std([e[key] for e in runs[k]["events"]], ddof=1) / np.sqrt(3)
            for k in labels
        ]
        ax.bar(range(len(labels)), vals, yerr=err, color=colors, capsize=3)
        ax.set_xticks(range(len(labels)), display, rotation=30, ha="right")
        ax.set_ylabel("Secondary hits/event")
        ax.set_title(title)
    save(
        fig,
        "Error bars: event SEM. Lower thresholds, finite path budgets and failed trajectories are model limitations, not plot cuts.",
    )
    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle("Full-event cost and transport failures")
    vals = [summary[k]["cpu_s_per_event"] for k in labels]
    axs[0].bar(range(len(labels)), vals, color=colors)
    axs[0].set_ylabel("Process CPU seconds/event, including CSV")
    axs[0].set_yscale("log")
    axs[0].set_xticks(range(len(labels)), display, rotation=30, ha="right")
    for i, v in enumerate(vals):
        axs[0].text(i, v * 1.1, f"{v:.2f}", ha="center")
    inner = labels[1:-1]
    axs[1].bar(
        range(4), [summary[k]["failures"] / 3 for k in inner], color=colors[1:-1]
    )
    axs[1].set_xticks(range(4), display[1:-1], rotation=30, ha="right")
    axs[1].set_ylabel("Failed charged trajectories/event")
    save(
        fig,
        "Main/G4 CPU: archived five-event measurement. New Fatras CPU: three events, one worker; 50000-step cap for bounded variants; 5000 for standard lower-threshold control.",
    )
    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle("Remaining gap: momentum and production process")
    for name, label, color in zip(labels, display, colors):
        axs[0].stairs(
            np.mean([e["pixel_secondary_pt"] for e in runs[name]["events"]], axis=0),
            np.arange(13),
            label=label.replace("\n", " "),
            color=color,
        )
    axs[0].set_yscale("log")
    axs[0].set_xticks(
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
    axs[0].set_xlabel("Hit-entry pT [MeV/c], interval")
    axs[0].set_ylabel("Secondary pixel hits/event/bin")
    axs[0].legend(fontsize=7)
    bottom = np.zeros(len(labels))
    for code, label in [
        ("1", "Decay"),
        ("2", "Conversion"),
        ("4", "Nuclear"),
        ("5", "Ionisation"),
        ("6", "Other"),
    ]:
        v = np.array(
            [
                np.mean([e["pixel_process"].get(code, 0) for e in runs[k]["events"]])
                for k in labels
            ]
        )
        axs[1].bar(range(len(labels)), v, bottom=bottom, label=label)
        bottom += v
    axs[1].set_xticks(range(len(labels)), display, rotation=30, ha="right")
    axs[1].set_ylabel("Secondary pixel hits/event")
    axs[1].legend(fontsize=8)
    save(
        fig,
        "Navigation cannot generate the missing ionisation electrons. Finite step and path budgets still prevent a closure claim.",
    )
    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle("Separating step-budget truncation from step-size dependence")
    capnames = ["bounded5", "bounded5-50k", "bounded2p5", "bounded2p5-50k"]
    caplabels = ["5 mm / 5k", "5 mm / 50k", "2.5 mm / 5k", "2.5 mm / 50k"]
    axs[0].bar(range(4), [summary[k]["pixel_secondary"] for k in capnames])
    axs[0].set_xticks(range(4), caplabels, rotation=25)
    axs[0].set_ylabel("Inclusive secondary pixel hits/event")
    axs[1].bar(range(4), [summary[k]["failures"] / 3 for k in capnames])
    axs[1].set_xticks(range(4), caplabels, rotation=25)
    axs[1].set_ylabel("Failed charged trajectories/event")
    save(
        fig,
        "The larger cap reduces failures to one trajectory per three events at each step size. It is a diagnostic, not a production default.",
    )
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.suptitle("Where charged transport spends time")
    x = np.arange(5)
    names = ["<5", "5–20", "20–50", "50–200", ">=200"]
    for i, k in enumerate(labels[1:-1]):
        st = runs[k]["metadata"]["navigation"]["statistics"]
        ax.bar(
            x + (i - 1.5) * 0.2,
            np.array(st["transport_seconds"]) / 3,
            0.2,
            label=display[i + 1].replace("\n", " "),
            color=colors[i + 1],
        )
    ax.set_xticks(x, names)
    ax.set_xlabel("Charged trajectory birth pT [MeV/c]")
    ax.set_ylabel("Charged-propagation wall seconds/event (one worker)")
    ax.legend()
    save(
        fig,
        "Includes navigation, stepping and physics along charged trajectories, including failures; excludes neutral propagation and CSV.\nDispatch is at birth pT<500 MeV; particles that subsequently slow do not switch navigator.",
    )
    probes = json.loads((a.work / "lowp-probes.json").read_text())
    selected = [
        next(d for d in probes if d["name"] == n)
        for n in ["native", "all5", "local5-bounded", "all2p5", "local2p5-bounded"]
    ]
    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle("Controlled probe: exact TryAll output with fewer intersections")
    for ax, key, ylabel in [
        (axs[0], "sequencer_cpu_seconds", "CPU seconds, one 432-muon event")
    ]:
        ax.bar(range(5), [d[key] for d in selected])
        ax.set_yscale("log")
        ax.set_xticks(
            range(5),
            [
                "Standard",
                "TryAll 5 mm",
                "Bounded 5 mm",
                "TryAll 2.5 mm",
                "Bounded 2.5 mm",
            ],
            rotation=30,
            ha="right",
        )
        ax.set_ylabel(ylabel)
    d = selected[2]["navigation"]["statistics"]
    axs[1].bar(
        ["Volume candidates", "After spatial pruning"], [d["available"], d["tested"]]
    )
    axs[1].set_yscale("log")
    axs[1].set_ylabel("Candidate intersection tests, 5 mm probe")
    save(
        fig,
        "Probe uses no interactions/decays. Bounded and TryAll CSVs match byte-for-byte at each step size.\nStatic geometry, one-worker external prototype; no claim of helix/G4 truth or step-size convergence.",
    )
