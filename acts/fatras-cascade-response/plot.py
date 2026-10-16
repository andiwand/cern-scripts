"""Inclusive comparison and controlled interaction-model diagnostics, PDF output."""

import argparse, csv, json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--preview", action="store_true")
a = p.parse_args()
w = a.work
d = json.loads((w / "analysis.json").read_text())
part = json.loads((w / "compton-partition.json").read_text())["mean"]
replay = json.loads((w / "photon-replay-summary.json").read_text())
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
    }
)
colors = ["#888888", "#2278b5", "#df7d20"]
page = 0
with PdfPages(a.output) as pdf:

    def save(
        fig,
        title,
        note,
        footer="Three ttbar + fixed PU200 events · all written ID hits · geometry unchanged · default G4 confined to ODD ID",
    ):
        global page
        page += 1
        fig.suptitle(title, fontsize=19, y=0.97)
        fig.subplots_adjust(left=0.08, right=0.97, top=0.82, bottom=0.23, wspace=0.3)
        fig.text(0.08, 0.105, note, fontsize=11, va="top")
        fig.text(0.03, 0.025, footer, fontsize=9)
        pdf.savefig(fig)
        if a.preview:
            fig.savefig(a.output.with_name(a.output.stem + f"-{page}.png"), dpi=120)
        plt.close(fig)

    fig, ax = plt.subplots(1, 3, figsize=(15, 8))
    labels = ["ACTS main", "Changed Fatras", "G4"]
    main = d["main"]
    cur = d["runs"]["Current"]["mean"]
    g4 = d["runs"]["Geant4"]["mean"]
    before = d["runs"]["Before"]["mean"]
    for axis, scope, title in [
        (ax[0], "pixel", "Pixel hits / event\n(labels: secondary counts)"),
        (ax[1], "ID", "ID hits / event\n(labels: secondary counts)"),
    ]:
        primary = [
            main[scope + "_primary"],
            cur[scope + "_totals"]["primary"],
            g4[scope + "_totals"]["primary"],
        ]
        secondary = [
            main[scope + "_secondary"],
            cur[scope + "_totals"]["secondary"],
            g4[scope + "_totals"]["secondary"],
        ]
        axis.bar(
            labels, np.array(primary) / 1000, color=colors, alpha=0.3, label="Primary"
        )
        axis.bar(
            labels,
            np.array(secondary) / 1000,
            bottom=np.array(primary) / 1000,
            color=colors,
            label="Secondary",
        )
        for i, n in enumerate(secondary):
            axis.text(
                i,
                (primary[i] + secondary[i]) / 1000 + 2,
                f"{n:,.0f}",
                ha="center",
                fontsize=10,
            )
        axis.set_title(title)
        axis.set_ylabel("Thousands of hits")
        axis.tick_params(axis="x", rotation=15)
        axis.set_ylim(0, max(np.array(primary) + secondary) / 1000 * 1.15)
    ax[0].legend(loc="upper left", fontsize=9)
    cpu = [
        d["timings"]["main_archived"],
        d["timings"]["current"]["median"],
        d["timings"]["geant4"],
    ]
    ax[2].bar(labels, cpu, color=colors)
    for i, n in enumerate(cpu):
        ax[2].text(i, n + 0.6, f"{n:.2f}", ha="center")
    ax[2].scatter(
        [1] * 3, d["timings"]["current"]["samples"], s=30, color="black", zorder=5
    )
    ax[2].set_title("CPU seconds / event")
    ax[2].tick_params(axis="x", rotation=15)
    deficit = lambda run, scope: 100 * (
        1 - run[scope + "_totals"]["secondary"] / g4[scope + "_totals"]["secondary"]
    )
    save(
        fig,
        "Interaction corrections: inclusive result and CPU",
        f'Secondary ID deficit: {deficit(before,"ID"):.2f}% → {deficit(cur,"ID"):.2f}%; pixel deficit: {deficit(before,"pixel"):.2f}% → {deficit(cur,"pixel"):.2f}%. The total gap has not closed.\nCPU: matched preceding-Fatras median {d["timings"]["control"]["median"]:.2f} s; current {cpu[1]:.2f} s. Main CPU is archived (five events); main hits use these three events.\nMain is pinned ACTS 300b664a3d. Current timing dots are three repeats of identical events; G4 timing is fresh.',
    )
    fig, ax = plt.subplots(1, 2, figsize=(15, 8))
    names = ["Before", "Current", "Geant4"]
    cs = ["#a4a4a4", "#2278b5", "#df7d20"]
    regions = {
        "Pixel barrel": [17],
        "Pixel endcaps": [16, 18],
        "Strip barrels": [24, 29],
        "Strip endcaps": [23, 25, 28, 30],
    }
    for i, name in enumerate(names):
        m = d["runs"][name]["mean"]
        vals = [
            sum(m["ID_volume"].get(str(v), 0) for v in vols) / 1000
            for vols in regions.values()
        ]
        ax[0].bar(
            np.arange(4) + (i - 1) * 0.25, vals, width=0.25, color=cs[i], label=name
        )
        keys = ["1", "2", "4", "5", "6"]
        ax[1].bar(
            np.arange(5) + (i - 1) * 0.25,
            [m["ID_process"].get(k, 0) / 1000 for k in keys],
            width=0.25,
            color=cs[i],
            label=name,
        )
    ax[0].set_xticks(range(4), regions, rotation=15)
    ax[0].set_title("Secondary hits by detector region")
    ax[1].set_xticks(
        range(5), ["Decay", "Conversion", "Nuclear", "Ionisation", "Other"], rotation=15
    )
    ax[1].set_title("Secondary hits by carrier birth process")
    for axis in ax:
        axis.set_ylabel("Thousands / event")
        axis.legend(fontsize=9)
    save(
        fig,
        "Inclusive totals still hide a spatial and process mismatch",
        "Birth-process labels describe the hit carrier, not disjoint causal cascades. The nuclear excess compensates missing EM response.\nBoth fixes are retained for interaction correctness. Neither the total nor the barrel/endcap shape demonstrates closure with G4.",
    )
    fig, ax = plt.subplots(1, 3, figsize=(16, 8))
    ph = [d["spectra"][n]["photons"]["brems_1.022_20MeV"] for n in names]
    ax[0].bar(names, np.array(ph) / 1000, color=cs)
    ax[0].set_title("Brems photons born at 1.022–20 MeV")
    ax[0].set_ylabel("Thousands / event")
    for i, n in enumerate(ph):
        ax[0].text(i, n / 1000 + 0.5, f"{n:,.0f}", ha="center")
    old = sum(part["Fatras/all/parent"].values())
    new = sum(d["spectra"]["Current"]["other_electron_hits_parent_process"].values())
    passive = sum(part["G4/passive/parent"].values())
    sensor = sum(part["G4/sensor/parent"].values())
    ax[1].bar(
        ["Before", "Current", "G4"],
        [old, new, passive],
        color=cs,
    )
    ax[1].bar(
        ["G4"],
        [sensor],
        bottom=[passive],
        color="#ccc",
        hatch="//",
        label="G4 sensor-born (deferred)",
    )
    ax[1].set_title("Direct Compton ID hits / event\n(labels: secondary counts)")
    ax[1].legend(fontsize=8)
    vals = [
        replay["fatras-photons-in-fatras"]["other_electron"],
        replay["g4-photons-in-fatras"]["other_electron"],
        replay["g4-photons-in-g4"]["compton/passive"],
    ]
    ax[2].bar(range(3), vals, color=["#999", "#2278b5", "#df7d20"])
    ax[2].set_xticks(
        range(3),
        [
            "Fatras photons\n→ Fatras",
            "G4 photons\n→ Fatras",
            "G4 photons\n→ G4 passive",
        ],
    )
    ax[2].set_title("Same-source replay: Compton hits")
    for i, n in enumerate(vals):
        ax[2].text(i, n + 15, str(n), ha="center")
    save(
        fig,
        "Compton: deficient photon supply plus a remaining response deficit",
        "Left and centre: inclusive event diagnostics. Right: separate replay of brems photons ≥100 keV from reference event 0, using preceding Fatras.\nCentre includes all 3,283 sensor-born hits/event (deferred). The separate source replay gives 2,323 sensor-born hits.\nThe source replay is diagnostic, not an additive recovered-hit prediction. No Compton cross-section multiplier is introduced.",
    )
    fig, ax = plt.subplots(1, 2, figsize=(15, 8))
    old = list(csv.DictReader((w / "stopping-before.csv").open()))
    new = list(csv.DictReader((w / "stopping-after.csv").open()))
    energies = [0.3, 1, 5, 20]

    def pick(data, slices):
        return [
            next(
                r
                for r in data
                if r["material"] == "G4_Si"
                and r["pdg"] == "11"
                and float(r["kinetic_MeV"]) == e
                and int(r["slices"]) == slices
                and float(r["thickness_mm"]) > 2 * float(r["range_mm"])
            )
            for e in energies
        ]

    for rows, label, color in [
        (pick(old, 1), "Old single slab", "#999"),
        (pick(new, 1), "Bounded integration", "#2278b5"),
        (pick(new, 1000), "1,000 material slices", "#39a05d"),
    ]:
        ax[0].errorbar(
            energies,
            [float(r["delta_mean"]) for r in rows],
            yerr=[float(r["delta_sem"]) for r in rows],
            marker="o",
            label=label,
            color=color,
        )
    ax[0].plot(
        energies,
        [float(r["g4_csda_delta"]) for r in pick(new, 1)],
        "--",
        color="#df7d20",
        label="G4 CSDA rate integral",
    )
    ax[0].set_xscale("log")
    ax[0].set_yscale("symlog", linthresh=0.02)
    ax[0].set_ylim(0, 12)
    ax[0].set_xlabel("Incident electron kinetic energy [MeV]")
    ax[0].set_ylabel("Knock-on electrons ≥100 keV / primary")
    ax[0].set_title("Stopping in silicon: three CSDA ranges")
    ax[0].legend(fontsize=9)
    col = list(csv.DictReader((w / "compton-column.csv").open()))
    for slices, color in [(1, "#999"), (100, "#39a05d"), (1000, "#2278b5")]:
        rows = [
            r
            for r in col
            if int(r["slices"]) == slices and float(r["thickness_mm"]) == 30
        ]
        ax[1].plot(
            [float(r["energy_MeV"]) for r in rows],
            [float(r["recoil_above_40keV_mean"]) for r in rows],
            marker="o",
            label=f"{slices:,} material slices",
            color=color,
        )
    ax[1].set_xscale("log")
    ax[1].set_xlabel("Incident photon energy [MeV]")
    ax[1].set_ylabel("Compton recoils ≥40 keV / photon")
    ax[1].set_title("30 mm Si: missing repeated scatters")
    ax[1].legend(fontsize=9)
    save(
        fig,
        "Controlled material columns isolate approximation errors",
        "Stopping: 2,000 trials/point, no radiation. G4 CSDA integrates model rates along mean energy loss; it is not a full stochastic G4 transport run.\nCompton: 10,000 trials/point, prescribed path column, no absorption or spatial scattering transport; photon tracking ends below 100 keV.\nThe one-scatter limitation remains for Compton. Diagnostic thresholds here do not cut any inclusive hit summary.",
        footer="Homogeneous-column experiments · no ODD geometry or material placement changes · no new runtime physics tables",
    )
