#!/usr/bin/env python3
"""Inclusive ODD summary: no momentum, time, multiplicity or ancestry cuts."""

import argparse, collections, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--main", type=Path, required=True)
p.add_argument("--fatras", type=Path, required=True)
p.add_argument("--geant4", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--cached", action="store_true")
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
BAR = ["particle_id_" + v for v in ["pv", "sv", "part", "gen", "subpart"]]
PT = [0, 0.001, 0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 10, 100, np.inf]
TIME = [0, 1, 10, 100, 1000, 10000, 1e6, np.inf]
labels = ["ACTS main", "Changed Fatras", "Geant4 default, ID only"]
colors = ["#777777", "#4c78a8", "#f28e2b"]
folders = [a.main, a.fatras, a.geant4]
cache = a.output / "inclusive-summary.json"


def csv(path, **kwargs):
    if not path.exists():
        path = path.with_suffix(".csv.gz")
    return pd.read_csv(path, **kwargs)


def counts(v):
    return {str(k): int(n) for k, n in collections.Counter(v).items()}


def mean(v):
    return float(np.mean(v))


def sem(v):
    return float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else None


if not a.cached:
    result = {
        "scope": "All recorded charged sensitive hits in the physical ODD ID world; no hit momentum/time cuts. Pixel counts are an explicitly labelled geometry subset. Identical generator input, restricted only to births inside the ID. Geant4 FTFP_BERT defaults, no extra global time kill. Native Fatras acceptance remains part of the model under test.",
        "runs": {},
    }
    for label, folder in zip(labels, folders):
        meta = json.loads((folder / "metadata.json").read_text())
        assert (
            meta["analysis_hit_p_min_GeV"] is None
            and meta["analysis_hit_pt_min_GeV"] is None
        )
        assert (
            meta["input_selection"]["p_min_GeV"] is None
            and meta["input_selection"]["pt_min_GeV"] is None
        )
        if label.startswith("Geant4"):
            assert (
                meta["geant4_explicit_time_max_ns"] is None
                and meta["geant4_world"]["world_solid"] == "G4Tubs"
            )
        rows = []
        for event in range(meta["events"]):
            h = csv(
                folder / f"event{event:09d}-hits.csv", dtype={"geometry_id": "uint64"}
            )
            truth = csv(
                folder / f"event{event:09d}-particles_simulated.csv",
                usecols=BAR + ["particle_type", "process", "vx", "vy", "vz"],
            )
            ids = pd.MultiIndex.from_frame(truth[BAR])
            assert ids.is_unique
            where = ids.get_indexer(pd.MultiIndex.from_frame(h[BAR]))
            assert np.all(where >= 0)
            vol = h.geometry_id.to_numpy() >> np.uint64(56)
            pixel = np.isin(vol, [16, 17, 18])
            secondary = h.particle_id_gen.to_numpy() > 0
            pt = np.hypot(h.tpx, h.tpy)
            mom = np.hypot(pt, h.tpz)
            row = {
                "event": event,
                "ID_primary": int((~secondary).sum()),
                "ID_secondary": int(secondary.sum()),
                "pixel_primary": int((pixel & ~secondary).sum()),
                "pixel_secondary": int((pixel & secondary).sum()),
                "volume_secondary": counts(vol[secondary]),
                "ID_secondary_pt": np.histogram(pt[secondary], PT)[0].tolist(),
                "pixel_secondary_pt": np.histogram(pt[pixel & secondary], PT)[
                    0
                ].tolist(),
                "ID_secondary_p": np.histogram(mom[secondary], PT)[0].tolist(),
                "ID_secondary_time": np.histogram(h.tt[secondary] / 299.792458, TIME)[
                    0
                ].tolist(),
            }
            # CSV time is ACTS native length unit; convert mm/c to ns.
            for region, mask in [("ID", secondary), ("pixel", pixel & secondary)]:
                row[region + "_process"] = counts(truth.process.to_numpy()[where[mask]])
                row[region + "_pdg"] = counts(
                    truth.particle_type.to_numpy()[where[mask]]
                )
            if label.startswith("Geant4"):
                row["outside_ID_hits"] = int(
                    (
                        (np.hypot(h.tx, h.ty) > 1202.001) | (np.abs(h.tz) > 4002.001)
                    ).sum()
                )
                row["outside_ID_births"] = int(
                    (
                        (np.hypot(truth.vx, truth.vy) > 1202.001)
                        | (np.abs(truth.vz) > 4002.001)
                    ).sum()
                )
                assert row["outside_ID_hits"] == 0 and row["outside_ID_births"] == 0
            rows.append(row)
            print(label, event, row["ID_secondary"], row["pixel_secondary"], flush=True)
        result["runs"][label] = {
            "folder": str(folder),
            "metadata": meta,
            "events": rows,
        }
    n = result["runs"][labels[0]]["metadata"]["events"]
    assert all(r["metadata"]["events"] == n for r in result["runs"].values())
    inputs = [
        r["metadata"]["input_selection"]["sha256"] for r in result["runs"].values()
    ]
    assert all(v == inputs[0] for v in inputs)
    result["summary"] = {}
    for label, r in result["runs"].items():
        result["summary"][label] = {
            k: {
                "mean": mean([e[k] for e in r["events"]]),
                "sem": sem([e[k] for e in r["events"]]),
            }
            for k in ["ID_primary", "ID_secondary", "pixel_primary", "pixel_secondary"]
        }
        result["summary"][label]["event_loop_cpu_s"] = (
            r["metadata"]["sequencer_cpu_seconds"] / n
        )
        result["summary"][label]["setup_cpu_s"] = r["metadata"]["setup_cpu_seconds"]
    cache.write_text(json.dumps(result, indent=2) + "\n")
else:
    result = json.loads(cache.read_text())
n = len(result["runs"][labels[0]]["events"])
plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42})
footer = f"{n} matched ttbar + 200 fixed pileup events, seed 42, Bz=2 T. No input or analysis momentum cuts; ID birth boundary only.\nGeant4 FTFP_BERT defaults, no additional time kill; physical world r=1202 mm, |z|=4002 mm. All recorded charged sensitive hits."
page = 0
with PdfPages(a.output / "inclusive_summary.pdf") as pdf:

    def save(fig, extra=""):
        global page
        page += 1
        fig.text(0.04, 0.025, footer + ("\n" + extra if extra else ""), fontsize=8)
        fig.tight_layout(rect=(0, 0.14, 1, 0.94))
        pdf.savefig(fig)
        fig.savefig(a.output / f"inclusive_page{page}.png", dpi=115)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Inclusive secondary hits — ACTS main, changed Fatras and Geant4")
    for ax, key, title in zip(
        axes,
        ["ID_secondary", "pixel_secondary"],
        ["All ID sensors", "Pixel sensors only"],
    ):
        values = [result["summary"][k][key]["mean"] for k in labels]
        errors = [result["summary"][k][key]["sem"] for k in labels]
        ax.bar(range(3), values, yerr=errors, capsize=4, color=colors)
        ax.set_xticks(range(3), labels, rotation=20, ha="right")
        ax.set_ylabel("Secondary hits/event")
        ax.set_title(title)
        for i, v in enumerate(values):
            ax.text(i, v + max(values) * 0.05, f"{v:,.0f}", ha="center")
        ax.set_ylim(0, max(v + e for v, e in zip(values, errors)) * 1.2)
    save(
        fig,
        "No normalization to Geant4. Error bars: event SEM; five events are a diagnostic sample.",
    )
    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.axis("off")
    fig.suptitle("Inclusive hit counts and measured CPU")
    rows = []
    for label in labels:
        s = result["summary"][label]
        rows.append(
            [
                label,
                *[
                    f"{s[k]['mean']:,.1f}"
                    for k in [
                        "ID_primary",
                        "ID_secondary",
                        "pixel_primary",
                        "pixel_secondary",
                    ]
                ],
                f"{s['event_loop_cpu_s']:.3f}",
                f"{s['setup_cpu_s']:.2f}",
            ]
        )
    t = ax.table(
        cellText=rows,
        colLabels=[
            "Simulation",
            "ID primary",
            "ID secondary",
            "Pixel primary",
            "Pixel secondary",
            "CPU s/event",
            "Setup CPU s/job",
        ],
        loc="center",
        cellLoc="center",
        colWidths=[0.23, 0.13, 0.13, 0.13, 0.13, 0.12, 0.13],
    )
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    t.scale(1, 2.2)
    save(
        fig,
        "One worker; sequential runs, identical CSV writers. Event-loop CPU includes simulation and I/O; setup includes geometry/data loading.\nFatras transport thresholds are model settings, not applied to the reference or to these plots.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Inclusive secondary-hit transverse momentum")
    ticks = [
        "<1",
        "1–5",
        "5–20",
        "20–50",
        "50–100",
        "100–200",
        "200–500",
        "500–1000",
        "1–2 GeV",
        "2–10 GeV",
        "10–100 GeV",
        ">100 GeV",
    ]
    for ax, key, title in zip(
        axes,
        ["ID_secondary_pt", "pixel_secondary_pt"],
        ["All ID sensors", "Pixel sensors only"],
    ):
        for label, c in zip(labels, colors):
            ax.plot(
                range(12),
                np.mean([e[key] for e in result["runs"][label]["events"]], axis=0),
                marker=".",
                label=label,
                color=c,
            )
        ax.set_xticks(range(12), ticks, rotation=60, ha="right")
        ax.set_xlabel("Hit-entry pT [MeV unless stated]")
        ax.set_ylabel("Hits/event/bin")
        ax.set_title(title)
        ax.legend(fontsize=8)
    save(
        fig,
        "First and last bins include the full low- and high-momentum tails; no momentum selection.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Inclusive secondary production and sensor volumes")
    procnames = [
        "Undefined",
        "Decay",
        "Conversion",
        "Bremsstrahlung",
        "Nuclear",
        "Ionisation",
        "Other",
    ]
    volumes = sorted(
        {
            int(v)
            for r in result["runs"].values()
            for e in r["events"]
            for v in e["volume_secondary"]
        }
    )
    for j, (label, c) in enumerate(zip(labels, colors)):
        rows = result["runs"][label]["events"]
        axes[0].bar(
            np.arange(7) + (j - 1) * 0.25,
            [mean([e["pixel_process"].get(str(k), 0) for e in rows]) for k in range(7)],
            width=0.25,
            label=label,
            color=c,
        )
        axes[1].plot(
            range(len(volumes)),
            [
                mean([e["volume_secondary"].get(str(v), 0) for e in rows])
                for v in volumes
            ],
            marker=".",
            label=label,
            color=c,
        )
    axes[0].set_xticks(range(7), procnames, rotation=35, ha="right")
    axes[0].set_ylabel("Secondary pixel hits/event")
    axes[0].legend(fontsize=8)
    axes[1].set_xticks(range(len(volumes)), volumes)
    axes[1].set_xlabel("ACTS volume ID")
    axes[1].set_ylabel("Secondary ID hits/event")
    axes[1].legend(fontsize=8)
    save(
        fig,
        "Process labels describe immediate particle creation. No truth-species or hit-multiplicity selection.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
    fig.suptitle("Inclusive species and arrival time")
    pdgs = [11, -11, 211, -211, 2212, -2212, 13, -13]
    names = ["e−", "e+", "pi+", "pi−", "p", "anti-p", "mu−", "mu+", "Other"]
    times = ["<1", "1–10", "10–100", "100–1000", "1–10 us", "10 us–1 ms", ">1 ms"]
    for j, (label, c) in enumerate(zip(labels, colors)):
        rows = result["runs"][label]["events"]
        ys = [mean([e["pixel_pdg"].get(str(k), 0) for e in rows]) for k in pdgs]
        ys.append(
            mean(
                [
                    sum(v for k, v in e["pixel_pdg"].items() if int(k) not in pdgs)
                    for e in rows
                ]
            )
        )
        axes[0].bar(np.arange(9) + (j - 1) * 0.25, ys, width=0.25, label=label, color=c)
        axes[1].plot(
            range(7),
            np.mean([e["ID_secondary_time"] for e in rows], axis=0),
            marker=".",
            label=label,
            color=c,
        )
    axes[0].set_xticks(range(9), names, rotation=30)
    axes[0].set_ylabel("Secondary pixel hits/event")
    axes[0].legend(fontsize=8)
    axes[1].set_xticks(range(7), times, rotation=35, ha="right")
    axes[1].set_xlabel("Arrival time [ns unless stated]")
    axes[1].set_ylabel("Secondary ID hits/event")
    axes[1].legend(fontsize=8)
    save(
        fig,
        "All arrival times are retained, including late hits. Geant4 retains its physics-list production thresholds; no Fatras-driven restriction.",
    )
