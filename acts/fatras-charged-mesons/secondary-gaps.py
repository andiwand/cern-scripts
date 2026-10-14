#!/usr/bin/env python3
"""Separate secondary production, hit acceptance and repeated sensor crossings."""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

BAR = ["particle_id_" + x for x in ("pv", "sv", "part", "gen", "subpart")]
PARENT = [x.replace("particle_id_", "parent_id_") for x in BAR]
PROCESSES = [
    "undefined",
    "decay",
    "conversion",
    "bremsstrahlung",
    "nuclear",
    "ionisation",
    "other",
]
PT = [0.05, 0.1, 0.2, 0.5, 1, 2, 1000000]


def analyse(folder, event):
    stem = f"event{event:09d}"
    h = pd.read_csv(
        folder / f"{stem}-hits.csv",
        usecols=BAR + ["geometry_id", "tpx", "tpy", "tpz"],
        dtype={"geometry_id": "uint64"},
    )
    pt = np.hypot(h.tpx, h.tpy)
    mask = (
        (h.particle_id_gen > 0)
        & np.isin(h.geometry_id.to_numpy() >> np.uint64(56), [16, 17, 18])
        & (pt >= 0.05)
        & (np.hypot(pt, h.tpz) >= 0.1)
    )
    h = h.loc[mask].copy()
    truth_path = folder / f"{stem}-particles_simulated.csv"
    if not truth_path.exists():
        truth_path = truth_path.with_suffix(".csv.gz")
    p = pd.read_csv(
        truth_path,
        usecols=BAR + PARENT + ["process", "particle_type", "px", "py", "pz", "q"],
    )
    ids = pd.MultiIndex.from_frame(p[BAR])
    assert ids.is_unique
    where = ids.get_indexer(pd.MultiIndex.from_frame(h[BAR]))
    assert np.all(where >= 0)
    h["truth_index"] = where
    h["process"] = p.process.to_numpy()[where]
    h["pdg"] = p.particle_type.to_numpy()[where]
    birth_pt = np.hypot(p.px, p.py)
    birth_accept = (
        (p.particle_id_gen > 0)
        & (p.q != 0)
        & (birth_pt >= 0.05)
        & (np.hypot(birth_pt, p.pz) >= 0.1)
    )
    out = {"event": event, "process": {}, "conversion_photon_source": {}}
    for code, name in enumerate(PROCESSES):
        hh = h[h.process == code]
        pairs = hh.drop_duplicates(["truth_index", "geometry_id"])
        sensors = pairs.groupby("truth_index").size()
        pdgs, counts = np.unique(hh.pdg, return_counts=True)
        unique_pdgs, unique_counts = np.unique(
            hh.drop_duplicates("truth_index").pdg, return_counts=True
        )
        out["process"][name] = {
            "hits": len(hh),
            "hit_particles": hh.truth_index.nunique(),
            "particle_sensor_pairs": len(pairs),
            "repeated_sensor_hits": len(hh) - len(pairs),
            "particles_at_least_3_sensors": int(sum(sensors >= 3)),
            "created_charged_birth_cuts": int(sum(birth_accept & (p.process == code))),
            "hit_pdg": {str(k): int(v) for k, v in zip(pdgs, counts)},
            "hit_particle_pdg": {
                str(k): int(v) for k, v in zip(unique_pdgs, unique_counts)
            },
            "hit_pt_bins": np.histogram(np.hypot(hh.tpx, hh.tpy), PT)[0].tolist(),
        }
    conv = h[h.process == 2]
    parents = ids.get_indexer(
        pd.MultiIndex.from_frame(p.iloc[conv.truth_index.to_numpy()][PARENT])
    )
    assert np.all(parents >= 0)
    photons = p.iloc[parents]
    assert np.all(photons.particle_type == 22)
    grand = ids.get_indexer(pd.MultiIndex.from_frame(photons[PARENT]))
    for proc, gen, ancestor in zip(photons.process, photons.particle_id_gen, grand):
        key = (
            "generator"
            if gen == 0
            else PROCESSES[proc]
            + ":"
            + (
                str(int(p.particle_type.iloc[ancestor]))
                if ancestor >= 0
                else "unresolved"
            )
        )
        out["conversion_photon_source"][key] = (
            out["conversion_photon_source"].get(key, 0) + 1
        )
    assert sum(out["conversion_photon_source"].values()) == len(conv)
    assert sum(v["hits"] for v in out["process"].values()) == len(h)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geant4", type=Path, required=True)
    ap.add_argument("--changed", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--events", type=int, default=20)
    ap.add_argument(
        "--plot-only",
        action="store_true",
        help="Reuse this output directory's saved diagnostic JSON",
    )
    a = ap.parse_args()
    data = {
        "pt_bins_GeV": PT,
        "caveats": "Common pixel hit-entry p>=0.1 GeV, pT>=0.05 GeV. Immediate creation process, not shower origin. Unique particles and particle/sensor pairs are counted per event. Birth-cut production includes the entire ID, not just pixel acceptance. Repeated sensor hits can be valid recrossings; three sensors is not a reconstruction efficiency. Photon source attributes conversion hits, not photon counts. One matched sample, physics model uncertainties not included.",
        "runs": {},
    }
    if a.plot_only:
        data = json.loads((a.output / "secondary-gaps.json").read_text())
        for name, folder in [("Geant4", a.geant4), ("Current Fatras", a.changed)]:
            assert data["runs"][name]["source"] == str(folder)
            assert len(data["runs"][name]["events"]) == a.events
    else:
        for name, folder in [("Geant4", a.geant4), ("Current Fatras", a.changed)]:
            meta = json.loads((folder / "metadata.json").read_text())
            if name == "Geant4":
                assert meta["geant4_world"]["world_solid"] == "G4Tubs"
            rows = []
            for e in range(a.events):
                rows.append(analyse(folder, e))
                print(name, e, flush=True)
            data["runs"][name] = {
                "source": str(folder),
                "metadata": meta,
                "events": rows,
            }
        a.output.mkdir(parents=True, exist_ok=True)
        (a.output / "secondary-gaps.json").write_text(json.dumps(data, indent=2) + "\n")
    processes = ["conversion", "decay", "nuclear"]
    colors = ["#333333", "#009e73"]
    with PdfPages(a.output / "secondary_gaps.pdf") as pdf:
        fig, axes = plt.subplots(2, 2, figsize=(11.7, 8.3))
        fig.suptitle("Where secondary pixel hits are missing", fontsize=18)
        for ax, (metric, title) in zip(
            axes.flat,
            [
                ("hits", "Accepted hits"),
                ("hit_particles", "Particles producing accepted hits"),
                ("particle_sensor_pairs", "Unique particle / sensor pairs"),
                ("repeated_sensor_hits", "Repeated hits on the same sensor"),
            ],
        ):
            for j, (name, run) in enumerate(data["runs"].items()):
                values = np.array(
                    [
                        [e["process"][p][metric] for p in processes]
                        for e in run["events"]
                    ]
                )
                ax.bar(
                    np.arange(3) + (j - 0.5) * 0.36,
                    values.mean(axis=0),
                    width=0.36,
                    color=colors[j],
                    label=name,
                    yerr=values.std(axis=0, ddof=1) / np.sqrt(a.events),
                    capsize=2,
                )
            ax.set_xticks(range(3), processes)
            ax.set_ylabel("mean / event")
            ax.set_title(title)
        axes[0, 0].legend()
        fig.text(
            0.05,
            0.025,
            "20 identical ttbar + PU200 events; ODD inner tracker, 2 T; p >= 100 MeV, pT >= 50 MeV at hit entry.\nPhysical Geant4 world r=1202 mm, |z|<=4002 mm. Error bars: event SEM; no model uncertainty.",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.075, 1, 0.95))
        pdf.savefig(fig)
        fig.savefig(a.output / "secondary_gaps_page1.png", dpi=120)
        plt.close(fig)
        fig, axes = plt.subplots(1, 3, figsize=(11.7, 5))
        fig.suptitle("Secondary-hit deficit versus transverse momentum", fontsize=17)
        for ax, proc in zip(axes, processes):
            vals = [
                np.array([e["process"][proc]["hit_pt_bins"] for e in run["events"]])
                for run in data["runs"].values()
            ]
            diff = vals[0] - vals[1]
            ax.bar(
                range(6),
                diff.mean(axis=0),
                yerr=diff.std(axis=0, ddof=1) / np.sqrt(a.events),
                capsize=2,
                color="#4477aa",
            )
            ax.set_xticks(
                range(6), [".05–.1", ".1–.2", ".2–.5", ".5–1", "1–2", ">2"], rotation=40
            )
            ax.axhline(0, color="gray", lw=0.7)
            ax.set_title(proc)
            ax.set_xlabel("hit-entry pT [GeV]")
        axes[0].set_ylabel("Geant4 − current Fatras hits / event")
        fig.text(
            0.05,
            0.025,
            "Same matched sample and cuts. Error bars: paired event SEM. These are process labels at particle creation, not independent recoverable gains.",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.1, 1, 0.94))
        pdf.savefig(fig)
        fig.savefig(a.output / "secondary_gaps_page2.png", dpi=120)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11.7, 5.8))
        fig.suptitle("Nuclear secondaries: particle composition matters", fontsize=17)
        groups = ["pions", "protons", "light ions", "other ions", "kaons", "other"]

        def species(pdg):
            pdg = int(pdg)
            if abs(pdg) == 211:
                return "pions"
            if pdg == 2212:
                return "protons"
            if abs(pdg) in [1000010020, 1000010030, 1000020030, 1000020040]:
                return "light ions"
            if abs(pdg) >= 1000000000:
                return "other ions"
            if abs(pdg) == 321:
                return "kaons"
            return "other"

        for ax, metric, title in zip(
            axes,
            ["hit_pdg", "hit_particle_pdg"],
            ["Accepted hits", "Particles producing accepted hits"],
        ):
            for j, (name, run) in enumerate(data["runs"].items()):
                vals = np.array(
                    [
                        [
                            sum(
                                v
                                for k, v in e["process"]["nuclear"][metric].items()
                                if species(k) == g
                            )
                            for g in groups
                        ]
                        for e in run["events"]
                    ]
                )
                ax.bar(
                    np.arange(len(groups)) + (j - 0.5) * 0.36,
                    vals.mean(axis=0),
                    width=0.36,
                    color=colors[j],
                    label=name,
                    yerr=vals.std(axis=0, ddof=1) / np.sqrt(a.events),
                    capsize=2,
                )
            ax.set_xticks(range(len(groups)), groups, rotation=35)
            ax.set_title(title)
            ax.set_ylabel("mean / event")
        axes[0].legend()
        fig.text(
            0.05,
            0.025,
            "Same sample and cuts. Light ions: deuteron, triton, helium-3 and alpha. Current Fatras folds fragments into an untransported residual.\nA total multiplicity adjustment cannot correct the opposite pion/proton discrepancies.",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.12, 1, 0.94))
        pdf.savefig(fig)
        fig.savefig(a.output / "secondary_gaps_page3.png", dpi=120)
        plt.close(fig)


if __name__ == "__main__":
    main()
