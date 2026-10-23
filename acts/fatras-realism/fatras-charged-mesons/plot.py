#!/usr/bin/env python3
"""Plot matched charged-meson ablations and independent physics checks."""

import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--results", type=Path, required=True)
p.add_argument("--calibration", type=Path, required=True)
p.add_argument(
    "--ablations",
    action="store_true",
    help="Show the historical charged-meson stages instead of ACTS main",
)
a = p.parse_args()
keys = (
    ["geant4", "baseline", "pion", "kaon", "full"]
    if a.ablations
    else ["geant4", "main", "full"]
)
labels = (
    [
        "Geant4",
        "Before meson additions",
        "+ pion decays",
        "+ K interactions",
        "+ K decays",
    ]
    if a.ablations
    else ["Geant4", "ACTS main", "Current Fatras"]
)
colors = (
    ["#333333", "#999999", "#0072b2", "#e69f00", "#009e73"]
    if a.ablations
    else ["#333333", "#999999", "#009e73"]
)
rows = {
    k: json.loads((a.results / f"{k}-ancestry.json").read_text())["events"]
    for k in keys
    if k != "main"
}
if not a.ablations:
    run_metadata = json.loads((a.results / "run-metadata.json").read_text())
    assert (
        run_metadata["geant4"].get("geant4_world", {}).get("world_solid") == "G4Tubs"
    ), "Require the ID-bounded Geant4 reference"
    metadata = run_metadata["fatras-em"]
    assert metadata["mode"] == "fatras-main" and not metadata["acts_worktree_dirty"]
    labels[1] += "\n" + metadata["acts_revision"][:10]
    for key, cache in [("geant4", "geant4"), ("full", "fatras")]:
        cached = json.loads((a.results / f"{cache}-{len(rows[key])}.json").read_text())
        assert [(r["event"], r["primary"], r["secondary"]) for r in rows[key]] == [
            (
                r["event"],
                r["pixel_common_primary_hits"],
                r["pixel_common_secondary_hits"],
            )
            for r in cached
        ], "Ancestry and shared comparison samples differ"
    main = json.loads((a.results / f"fatras-em-{len(rows['geant4'])}.json").read_text())
    # Main has neither decay nor nuclear creation. Check this before assigning
    # their exactly zero contributions; no missing ancestry is inferred.
    assert all(r["pixel_common_hits_by_process"][i] == 0 for r in main for i in [1, 4])
    rows["main"] = [
        dict(
            event=r["event"],
            primary=r["pixel_common_primary_hits"],
            secondary=r["pixel_common_secondary_hits"],
            process=dict(
                zip(
                    [
                        "undefined",
                        "decay",
                        "conversion",
                        "bremsstrahlung",
                        "nuclear",
                        "ionisation",
                        "other",
                    ],
                    r["pixel_common_hits_by_process"],
                )
            ),
            parent_pdg={"decay": {}, "nuclear": {}},
        )
        for r in main
    ]
    # The undefined process includes primary hits in the shared cache.
    for r in rows["main"]:
        r["process"]["undefined"] -= r["primary"]
baseline = "baseline" if a.ablations else "main"
positions = np.arange(len(keys))
n = len(rows["geant4"])
assert n > 1 and all([r["event"] for r in v] == list(range(n)) for v in rows.values())
sem = lambda x: float(np.std(x, ddof=1) / np.sqrt(len(x)))
values = lambda k, f: np.array([r[f] for r in rows[k]], float)
ref = values("geant4", "secondary")
direct = lambda k, process, pdgs: np.array(
    [sum(r["parent_pdg"][process].get(str(p), 0) for p in pdgs) for r in rows[k]]
)
summary = {
    "events": n,
    "hits": {},
    "increments": {},
    "calibration": {},
    "decay_spectra": {},
}
for k in keys:
    x = values(k, "secondary")
    ratio = x.mean() / ref.mean()
    summary["hits"][k] = {
        "primary": values(k, "primary").mean(),
        "secondary": x.mean(),
        "ratio": ratio,
        "ratio_paired_sem": sem(x - ratio * ref) / ref.mean(),
        "process": {
            p: np.mean([r["process"][p] for r in rows[k]])
            for p in rows[k][0]["process"]
        },
        "pion_decay": direct(k, "decay", [211, -211]).mean(),
        "kaon_decay": direct(k, "decay", [321, -321]).mean(),
        "kaon_nuclear": direct(k, "nuclear", [321, -321]).mean(),
    }
for before, after in (zip(keys[1:-1], keys[2:]) if a.ablations else []):
    d = values(after, "secondary") - values(before, "secondary")
    summary["increments"][after] = {"mean": d.mean(), "paired_sem": sem(d)}
d = values("full", "secondary") - values(baseline, "secondary")
summary["gain"] = {
    "mean": d.mean(),
    "paired_sem": sem(d),
    "relative": d.mean() / values(baseline, "secondary").mean(),
    "gap_closed": d.mean() / (ref.mean() - values(baseline, "secondary").mean()),
}
book = PdfPages(
    a.results
    / (
        "charged_meson_ablations.pdf"
        if a.ablations
        else "charged_meson_diagnostics.pdf"
    )
)


def save(fig, note):
    fig.text(0.04, 0.025, note, fontsize=9)
    fig.tight_layout(rect=[0, 0.065, 1, 0.94])
    prefix = "ablation" if a.ablations else "diagnostic"
    fig.savefig(a.results / f"{prefix}_page{book.get_pagecount()+1}.png", dpi=110)
    book.savefig(fig)
    plt.close(fig)


fig, ax = plt.subplots(1, 2, figsize=(11.7, 8.3))
fig.suptitle(
    (
        "Fatras versus ACTS main: matched ODD pixel hits"
        if not a.ablations
        else "Charged mesons: matched ODD pixel hits"
    ),
    fontsize=17,
)
for axis, f in zip(ax, ["primary", "secondary"]):
    y = [values(k, f).mean() for k in keys]
    e = [sem(values(k, f)) for k in keys]
    axis.bar(positions, y, yerr=e, color=colors)
    axis.set_xticks(positions, labels, rotation=30, ha="right")
    axis.set_ylabel("hits / event")
    axis.set_title(
        "Generator-particle hits" if f == "primary" else "Simulation-secondary hits"
    )
    for i, z in enumerate(y):
        axis.text(i, z + max(y) * 0.035, f"{z:,.0f}", ha="center", fontsize=10)
    axis.set_ylim(0, max(y) * 1.2)
save(
    fig,
    "20 identical ttbar + PU200 events; 2 T, ODD tracker; pixel hit-entry p >= 0.1 GeV, pT >= 0.05 GeV.\n"
    + (
        "Main: pMin = 0.1 GeV; no pT transport cut. Same corrected material map. Bars: event SEM."
        if not a.ablations
        else "Bars: event SEM. Increments include altered cascades and random-number history."
    ),
)
fig, ax = plt.subplots(1, 2, figsize=(11.7, 8.3))
fig.suptitle("What changes the secondary-hit yield?", fontsize=17)
processes = ["decay", "nuclear", "conversion"]
bottom = np.zeros(len(keys))
for proc, c in zip(processes, ["#0072b2", "#e69f00", "#009e73"]):
    y = np.array([summary["hits"][k]["process"][proc] for k in keys])
    ax[0].bar(positions, y, bottom=bottom, label=proc, color=c)
    bottom += y
ax[0].set_xticks(positions, labels, rotation=30, ha="right")
ax[0].legend()
ax[0].set_ylabel("hits / event")
for i, (field, label) in enumerate(
    [
        ("pion_decay", "pion decay"),
        ("kaon_nuclear", "K nuclear"),
        ("kaon_decay", "K decay"),
    ]
):
    for j, k in enumerate(keys):
        ax[1].bar(
            i + (j - (len(keys) - 1) / 2) * 0.14,
            summary["hits"][k][field],
            0.14,
            color=colors[j],
            label=labels[j] if i == 0 else None,
        )
ax[1].set_xticks(range(3), ["pion decay", "K nuclear", "K decay"])
ax[1].legend(fontsize=9)
ax[1].set_ylabel("direct parent-origin hits / event")
save(
    fig,
    "Immediate parent attribution, not full shower ancestry. Decays can replace parent hits and compete with interactions.\nGeant4 nuclear contributions include elastic and at-rest processes; these are not all recoverable by inelastic tables.",
)
cal = json.loads(a.calibration.read_text())
fig, ax = plt.subplots(2, 2, figsize=(11.7, 8.3))
fig.suptitle("Charged-kaon tables: independent midpoint validation", fontsize=17)
for j, pdg in enumerate([321, -321]):
    q = [r for r in cal if r["pdg"] == pdg]
    x = np.array([r["p_GeV"] for r in q])
    ratio = np.array([r["model_rate"] / r["reference_rate"] - 1 for r in q])
    diff = np.array([r["model_charged_mean"] - r["reference_charged_mean"] for r in q])
    err = np.array(
        [np.hypot(r["model_charged_se"], r["reference_charged_se"]) for r in q]
    )
    summary["calibration"][str(pdg)] = {
        "max_abs_rate_relative": float(np.max(np.abs(ratio))),
        "mean_charged_difference": float(diff.mean()),
    }
    ax[0, j].plot(x, 100 * ratio)
    ax[1, j].errorbar(x, diff, yerr=err, fmt=".", ms=3, elinewidth=0.5)
    for axis in ax[:, j]:
        axis.set_xscale("log")
        axis.axhline(0, color="gray", lw=0.7)
        axis.set_xlabel("momentum [GeV]")
        axis.set_title("K+" if pdg > 0 else "K-")
ax[0, 0].set_ylabel("rate difference [%]")
ax[1, 0].set_ylabel("charged multiplicity difference")
save(
    fig,
    "FTFP_BERT 11.3.2 Si; 512 events/node, 256 per independent midpoint. Rates interpolated; lower-node final states.\nNo ODD tuning. Local L0 scales interaction probability; target composition and fragment transport remain approximations.",
)
dec = pd.read_csv(a.results / "decay-reference.csv")
fig, ax = plt.subplots(2, 2, figsize=(11.7, 8.3))
fig.suptitle("Native K+ decay spectra versus Geant4", fontsize=17)
channels = [
    ("-211:211:211:", "three charged pions"),
    ("111:111:211:", "charged pion + two pi0"),
    ("-11:12:111:", "electron + neutrino + pi0"),
    ("-13:14:111:", "muon + neutrino + pi0"),
]
x = (np.arange(100) + 0.5) * 0.003
for axis, (channel, title) in zip(ax.flat, channels):
    means = {}
    for model, color in [("geant4", "#333333"), ("native", "#009e73")]:
        r = dec[
            (dec.pdg == 321) & (dec.model == model) & (dec.channel == channel)
        ].iloc[0]
        y = r[[f"bin{i}" for i in range(100)]].to_numpy(float)
        axis.step(x, y / y.sum() / 0.003, where="mid", label=model, color=color)
        means[model] = r.energy_sum_GeV / r.charged
    axis.set_title(title)
    axis.set_xlabel("charged daughter rest-frame energy [GeV]")
    axis.set_ylabel("normalized density")
    axis.legend()
    summary["decay_spectra"][channel] = means
save(
    fig,
    "100,000 decays per species/model. Native three-body modes use constant-matrix-element phase space.\nSemileptonic shape differences are explicit model limitations. Charge conjugates and branching counts are archived.",
)
book.close()
(
    a.results
    / (
        "charged-meson-summary.json"
        if a.ablations
        else "charged-meson-summary-main.json"
    )
).write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
