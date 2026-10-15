"""Inclusive ODD soft-secondary validation and CPU, with explicit reference provenance."""

import argparse, csv, json, math, collections, io, gzip
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser()
p.add_argument("--work", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--reference", type=Path, required=True)
p.add_argument(
    "--transport-reference",
    type=Path,
    default=Path.home()
    / "cern/scripts/acts/fatras-low-momentum/results/2026-10-15/summary.json",
)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
bar = ["particle_id_" + s for s in ["pv", "sv", "part", "gen", "subpart"]]
par = ["parent_id_" + s for s in ["pv", "sv", "part", "gen", "subpart"]]
ptbins = [0, 0.001, 0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 10, 100, float("inf")]
labels = {
    "standard-final": "Fatras standard navigation",
    "bounded-photon": "Bounded: photon acceptance",
    "bounded-ionisation": "Bounded: + ionisation",
    "bounded-all": "Bounded: + decays",
    "bounded-soft": "Bounded: softer transport",
    "geant4": "Geant4 default, ID only",
}
runs = {}
attribution = {}
for folder, label in labels.items():
    root = a.work / folder
    if not (root / "metadata.json").exists():
        continue
    meta = json.loads((root / "metadata.json").read_text())
    events = []
    for ev in range(meta["events"]):

        def rows(suffix):
            path = root / f"event{ev:09d}-{suffix}.csv"
            with (
                path.open()
                if path.exists()
                else gzip.open(path.with_suffix(".csv.gz"), "rt")
            ) as f:
                yield from csv.DictReader(f)

        truth = {tuple(r[k] for k in bar): r for r in rows("particles_simulated")}
        counts = collections.Counter()
        proc = collections.Counter()
        pdg = collections.Counter()
        parents = collections.Counter()
        pt = []
        local = collections.Counter()
        birthcut = collections.Counter()
        birthprocess = collections.Counter(
            r["process"] for r in truth.values() if int(r["particle_id_gen"]) > 0
        )
        for h in rows("hits"):
            pos = np.array([float(h[k]) for k in ["tx", "ty", "tz"]])
            assert np.hypot(*pos[:2]) <= 1202.001 and abs(pos[2]) <= 4002.001
            pix = int(h["geometry_id"]) >> 56 in [16, 17, 18]
            sec = int(h["particle_id_gen"]) > 0
            suffix = "secondary" if sec else "primary"
            counts["ID_" + suffix] += 1
            counts["pixel_" + suffix] += pix
            if not (sec and pix):
                continue
            t = truth[tuple(h[k] for k in bar)]
            proc[t["process"]] += 1
            pdg[t["particle_type"]] += 1
            pt.append(math.hypot(float(h["tpx"]), float(h["tpy"])))
            birth = np.array([float(t[k]) for k in ["vx", "vy", "vz"]])
            local[t["process"]] += np.linalg.norm(pos - birth) < 1
            px, py, pz = [float(t[k]) for k in ["px", "py", "pz"]]
            birthcut[t["process"]] += (
                math.sqrt(px * px + py * py + pz * pz) < 0.02
                or math.hypot(px, py) < 0.005
            )
            parent = truth.get(tuple(t[k] for k in par))
            parents[
                t["process"] + ":" + (parent["particle_type"] if parent else "unknown")
            ] += 1
        row = dict(counts)
        row.update(
            event=ev,
            pixel_process=dict(proc),
            pixel_pdg=dict(pdg),
            pixel_secondary_pt=np.histogram(pt, ptbins)[0].tolist(),
            pixel_birth_distance_lt_1mm=dict(local),
            pixel_birth_below_charged_cuts=dict(birthcut),
            pixel_parent_pdg=dict(parents),
            retained_secondary_process=dict(birthprocess),
        )
        events.append(row)
    runs[label] = {"metadata": meta, "events": events}
ref = json.loads(a.reference.read_text())
for key in ["ACTS main"]:
    runs[key] = {
        "metadata": ref["runs"][key]["metadata"],
        "events": ref["runs"][key]["events"][:3],
    }
oldpath = a.transport_reference
old = json.loads(oldpath.read_text())
runs["Bounded transport control"] = old["runs"]["bounded5-50k"]
summary = {}
for name, run in runs.items():
    ev = run["events"]
    m = run["metadata"]
    summary[name] = {
        k: float(np.mean([e[k] for e in ev]))
        for k in ["pixel_secondary", "ID_secondary", "pixel_primary", "ID_primary"]
    }
    summary[name]["cpu_s_per_event"] = m["sequencer_cpu_seconds"] / m["events"]
    summary[name]["events"] = len(ev)
    for field in [
        "pixel_process",
        "pixel_birth_distance_lt_1mm",
        "pixel_birth_below_charged_cuts",
        "pixel_parent_pdg",
        "retained_secondary_process",
    ]:
        keys = set().union(*(e.get(field, {}) for e in ev))
        summary[name][field] = {
            k: sum(e.get(field, {}).get(k, 0) for e in ev) / len(ev) for k in keys
        }
(a.output / "summary.json").write_text(
    json.dumps(
        {
            "runs": runs,
            "summary": summary,
            "scope": "Inclusive hits, no analysis momentum/time cuts. Three matched events; ACTS-main CPU archived five-event sample. Bounded standard cuts p=20MeV,pT=5MeV,5mm search,4 turns,50k steps. Softer variant separately recorded in metadata. Production ionisation cut100keV; retained truth excludes charged tracks rejected before transport.",
        },
        indent=2,
        default=lambda o: o.item(),
    )
)
print(
    json.dumps(
        {
            k: {x: y for x, y in v.items() if not isinstance(y, dict)}
            for k, v in summary.items()
        },
        indent=2,
    )
)
order = [
    n
    for n in [
        "ACTS main",
        "Fatras standard navigation",
        "Bounded transport control",
        "Bounded: photon acceptance",
        "Bounded: + ionisation",
        "Bounded: + decays",
        "Bounded: softer transport",
        "Geant4 default, ID only",
    ]
    if n in runs
]
display = [
    n.replace("Bounded: ", "")
    .replace("Fatras standard navigation", "Fatras\nstandard nav")
    .replace("Geant4 default, ID only", "Geant4\nID only")
    .replace("Bounded transport control", "Bounded\ncontrol")
    .replace("ACTS main", "ACTS main\n300b664a3d")
    for n in order
]
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
footer = "3 matched ttbar + fixed PU200 events, 2 T; inclusive input and hits, no analysis momentum/time cuts.\nG4 default FTFP_BERT; physical ID r=1202 mm, |z|=4002 mm; no added G4 time kill."
with PdfPages(a.output / "soft_secondaries.pdf") as pdf:

    def save(fig, note=""):
        fig.text(0.04, 0.025, footer + "\n" + note, fontsize=8)
        fig.tight_layout(rect=(0, 0.15, 1, 0.94))
        pdf.savefig(fig)
        plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle(
        "Inclusive secondary hits: production improvements and remaining transport gap"
    )
    for ax, key, title in zip(
        axs, ["pixel_secondary", "ID_secondary"], ["Pixel sensors", "All ID sensors"]
    ):
        vals = [summary[n][key] for n in order]
        err = [
            np.std([e[key] for e in runs[n]["events"]], ddof=1)
            / np.sqrt(len(runs[n]["events"]))
            for n in order
        ]
        ax.bar(range(len(order)), vals, yerr=err, capsize=2)
        ax.set_xticks(range(len(order)), display, rotation=40, ha="right")
        ax.set_ylabel("Secondary hits/event")
        ax.set_title(title)
    save(
        fig,
        "Bounded: p>=20 MeV, pT>=5 MeV. Softer: p>=0.2 MeV, pT>=0.05 MeV; both four turns / 50k steps.\n"
        "Error bars: event SEM; small sample and different random streams after each physics change.",
    )
    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle("CPU cost and hit-production processes")
    vals = [summary[n]["cpu_s_per_event"] for n in order]
    axs[0].bar(range(len(order)), vals)
    axs[0].set_yscale("log")
    axs[0].set_ylabel("Process CPU s/event, including CSV")
    axs[0].set_xticks(range(len(order)), display, rotation=40, ha="right")
    for i, v in enumerate(vals):
        axs[0].text(i, v * 1.08, f"{v:.2f}", ha="center", fontsize=8)
    bottom = np.zeros(len(order))
    for code, label in [
        ("0", "Unspecified"),
        ("1", "Decay"),
        ("2", "Conversion"),
        ("3", "Bremsstrahlung"),
        ("4", "Nuclear"),
        ("5", "Ionisation"),
        ("6", "Other"),
    ]:
        vals = np.array([summary[n]["pixel_process"].get(code, 0) for n in order])
        axs[1].bar(range(len(order)), vals, bottom=bottom, label=label)
        bottom += vals
    axs[1].set_xticks(range(len(order)), display, rotation=40, ha="right")
    axs[1].set_ylabel("Secondary pixel hits/event")
    axs[1].legend(fontsize=8)
    save(
        fig,
        "Main reference CPU: archived five-event sample. Other measurements: three events, one worker. Bounded search remains a prototype.",
    )
    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle("Where the remaining soft-hit deficit lives")
    for n in [
        "ACTS main",
        "Bounded transport control",
        "Bounded: + decays",
        "Bounded: softer transport",
        "Geant4 default, ID only",
    ]:
        if n in runs:
            axs[0].stairs(
                np.mean([e["pixel_secondary_pt"] for e in runs[n]["events"]], axis=0),
                np.arange(13),
                label=n,
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
    axs[0].set_xlabel("Hit-entry pT [MeV], interval")
    axs[0].set_ylabel("Secondary pixel hits/event/bin")
    axs[0].legend(fontsize=7)
    g = summary["Geant4 default, ID only"]
    codes = ["5", "2", "1"]
    x = np.arange(3)
    for offset, key, label in [
        (-0.25, "pixel_process", "All G4 hits"),
        (0, "pixel_birth_below_charged_cuts", "Born below p20/pT5 MeV"),
        (0.25, "pixel_birth_distance_lt_1mm", "Within 1 mm of birth"),
    ]:
        axs[1].bar(
            x + offset, [g[key].get(c, 0) for c in codes], width=0.25, label=label
        )
    axs[1].set_xticks(x, ["Ionisation", "Conversion", "Decay"])
    axs[1].set_ylabel("Geant4 secondary pixel hits/event")
    axs[1].legend(fontsize=8)
    save(
        fig,
        "Birth-cut and distance categories overlap. Distance <1 mm is a diagnostic, not proof that birth and hit occupy the same sensor.",
    )
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.suptitle("Decay-origin pixel hits: which parents still matter?")
    groups = [
        ("K-short", ["310"]),
        ("mu+", ["-13"]),
        ("charged pions", ["211", "-211"]),
        ("Lambda / anti-Lambda", ["3122", "-3122"]),
        ("charged kaons", ["321", "-321"]),
        ("pi0 Dalitz", ["111"]),
    ]
    names = [
        n
        for n in [
            "Bounded: + decays",
            "Bounded: softer transport",
            "Geant4 default, ID only",
        ]
        if n in runs
    ]
    for i, n in enumerate(names):
        vals = [
            sum(summary[n]["pixel_parent_pdg"].get("1:" + pdg, 0) for pdg in pdgs)
            for _, pdgs in groups
        ]
        ax.bar(np.arange(len(groups)) + (i - 1) * 0.25, vals, width=0.25, label=n)
    ax.set_xticks(np.arange(len(groups)), [label for label, _ in groups], rotation=20)
    ax.set_ylabel("Secondary pixel hits/event, carrier born in decay")
    ax.legend()
    save(
        fig,
        "Nuclear pi0 daughters remain folded into the nuclear vertex in Fatras. Parent categories shown are not exhaustive.",
    )

    # Direct model check against local Geant4 analytic ionisation models.
    path = a.work / "ionisation-reference.csv"
    if path.exists():
        text = path.read_text()
        text = text[text.index("pdg,") :]
        rows = list(csv.DictReader(io.StringIO(text)))
        fig, axs = plt.subplots(1, 2, figsize=(12, 8))
        fig.suptitle(
            "Ionisation model check: 10 micrometres of silicon, 1 million trials/point"
        )
        for pdg, mark in [("e-", "o"), ("e+", "s"), ("mu-", "^"), ("p", "D")]:
            rr = [r for r in rows if r["pdg"] == pdg and float(r["cut_MeV"]) == 0.1]
            x = [float(r["kinetic_MeV"]) for r in rr]
            rrate = [r for r in rr if float(r["g4_mean_electrons"]) > 0]
            axs[0].errorbar(
                [float(r["kinetic_MeV"]) for r in rrate],
                [
                    float(r["mean_electrons"]) / float(r["g4_mean_electrons"])
                    for r in rrate
                ],
                yerr=[
                    math.sqrt(float(r["mean_electrons"]) / float(r["n"]))
                    / float(r["g4_mean_electrons"])
                    for r in rrate
                ],
                marker=mark,
                label=pdg,
            )
            axs[1].errorbar(
                x,
                [float(r["mean_loss_MeV"]) / float(r["g4_mean_loss_MeV"]) for r in rr],
                yerr=[
                    float(r["sem_loss_MeV"]) / float(r["g4_mean_loss_MeV"]) for r in rr
                ],
                marker=mark,
                label=pdg,
            )
        for ax in axs:
            ax.set_xscale("log")
            ax.axhline(1, color="grey", ls="--")
            ax.set_xlabel("Incident kinetic energy [MeV]")
            ax.legend()
        axs[0].set_ylabel("Electron multiplicity / Geant4 cross section")
        axs[1].set_ylabel("Mean loss / Geant4 unrestricted mean")
        save(
            fig,
            "100 keV electron production threshold. Fatras: thin-slab approximation, simplified density correction; no sub-cut straggling. G4 analytic rate/loss, not full transport.",
        )
