"""Uncut inclusive comparison, regional/process diagnostics and slab response."""

import argparse
import json
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
d = json.loads((a.work / "analysis.json").read_text())
plt.rcParams.update(
    {
        "font.size": 11,
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
colors = ["#888888", "#2278b5", "#df7d20"]
cur = d["runs"]["Current"]["mean"]
before = d["runs"]["Before"]["mean"]
g4 = d["runs"]["Geant4"]["mean"]
page = 0
with PdfPages(a.output) as pdf:

    def save(
        fig,
        title,
        note,
        footer="Three ttbar + fixed PU200 events · all written ID hits · unchanged geometry · default G4 confined to ODD ID",
    ):
        global page
        page += 1
        fig.suptitle(title, fontsize=19, y=0.97)
        fig.subplots_adjust(left=0.075, right=0.975, top=0.81, bottom=0.25, wspace=0.35)
        fig.text(0.075, 0.14, note, fontsize=11, va="top")
        fig.text(0.03, 0.025, footer, fontsize=9)
        pdf.savefig(fig)
        if a.preview:
            fig.savefig(a.output.with_name(a.output.stem + f"-{page}.png"), dpi=120)
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 8))
    labels = ["ACTS main", "Changed Fatras", "Geant4"]
    for ax, scope in zip(axes[:2], ["pixel", "ID"]):
        pri = [
            d["main"][scope + "_primary"],
            cur[scope + "_totals"]["primary"],
            g4[scope + "_totals"]["primary"],
        ]
        sec = [
            d["main"][scope + "_secondary"],
            cur[scope + "_totals"]["secondary"],
            g4[scope + "_totals"]["secondary"],
        ]
        ax.bar(labels, np.array(pri) / 1000, color=colors, alpha=0.3, label="Primary")
        ax.bar(
            labels,
            np.array(sec) / 1000,
            bottom=np.array(pri) / 1000,
            color=colors,
            label="Secondary",
        )
        for i, n in enumerate(sec):
            ax.text(i, (pri[i] + n) / 1000 + 2, f"{n:,.0f}", ha="center", fontsize=10)
        ax.set_ylim(0, max(np.array(pri) + sec) / 1000 * 1.15)
        ax.set_ylabel("Thousands of hits / event")
        ax.set_title(
            f"{("Pixel" if scope == "pixel" else "ID")} hits\n(labels: secondary counts)"
        )
        ax.tick_params(axis="x", rotation=15)
    axes[0].legend(fontsize=9)
    cpu = [
        d["timings"]["main_archived"],
        d["timings"]["current"]["median"],
        d["timings"]["geant4_archived"],
    ]
    axes[2].bar(labels, cpu, color=colors)
    axes[2].scatter(
        [1] * 3, d["timings"]["current"]["samples"], color="black", s=25, zorder=5
    )
    for i, n in enumerate(cpu):
        axes[2].text(i, n + 1.6, f"{n:.2f}", ha="center")
    axes[2].set_title("CPU seconds / event")
    axes[2].tick_params(axis="x", rotation=15)
    gap = lambda m, s: 100 * (
        1 - m[s + "_totals"]["secondary"] / g4[s + "_totals"]["secondary"]
    )
    save(
        fig,
        "Charged birth-material transport: inclusive hits and CPU",
        f'Secondary ID deficit: {gap(before,"ID"):.2f}% → {gap(cur,"ID"):.2f}%; pixel deficit: {gap(before,"pixel"):.2f}% → {gap(cur,"pixel"):.2f}%.\n'
        f'Matched CPU medians: Fatras ae02eeb5fb {d["timings"]["control"]["median"]:.2f} s; changed {cpu[1]:.2f} s (three serial repeats each).\n'
        "ACTS main is pinned to 300b664a3d. Main CPU: archived five-event run; G4 CPU: archived same-day three-event run.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    regions = {
        "Pixel barrel": [17],
        "Pixel endcaps": [16, 18],
        "Strip barrels": [24, 29],
        "Strip endcaps": [23, 25, 28, 30],
    }
    for i, (name, m) in enumerate([("Changed Fatras", cur), ("Geant4", g4)]):
        axes[0].bar(
            np.arange(4) + (i - 0.5) * 0.35,
            [
                sum(m["ID_volume"].get(str(v), 0) for v in ids) / 1000
                for ids in regions.values()
            ],
            width=0.35,
            color=colors[i + 1],
            label=name,
        )
        axes[1].bar(
            np.arange(5) + (i - 0.5) * 0.35,
            [m["ID_process"].get(k, 0) / 1000 for k in ["1", "2", "4", "5", "6"]],
            width=0.35,
            color=colors[i + 1],
            label=name,
        )
    axes[0].set_xticks(range(4), regions, rotation=15)
    axes[1].set_xticks(
        range(5), ["Decay", "Conversion", "Nuclear", "Ionisation", "Other"], rotation=15
    )
    axes[0].set_title("Secondary hits by detector region")
    axes[1].set_title("Secondary hits by carrier birth process")
    for ax in axes:
        ax.set_ylabel("Thousands / event")
        ax.legend(fontsize=9)
    save(
        fig,
        "Remaining spatial and process differences",
        "Birth-process labels describe the hit carrier; they are not additive causal contributions to the deficit.\n"
        "The material map and sensor material placement are unchanged. Charged birth columns are included; birth-sensor deposition remains deferred.\n"
        "No cross-section multiplier, occupancy correction or noise-hit injection is applied.",
    )

    def slab(
        pdg,
        energy,
        thickness,
        profile,
        backend="fatras",
        slices=1,
        angular=0.04,
        loss=0.02,
    ):
        key = (
            f"{pdg}-{energy}-{thickness}-{profile}-{backend}-{slices}-{angular}-{loss}"
        )
        return d["slabs"][key]["metrics"]

    fig, axes = plt.subplots(1, 3, figsize=(16, 8))
    variants = [
        ("Fatras\ndefault", slab(11, 20, 30, "transport")),
        ("Fatras\n1000 slices", slab(11, 20, 30, "transport", slices=1000)),
        (
            "Fatras\ntighter",
            slab(11, 20, 30, "transport", angular=0.01, loss=0.01),
        ),
        ("G4\nmatched", slab(11, 20, 30, "transport", "g4")),
    ]
    for ax, (metric, label) in zip(
        axes,
        [
            ("escape_charged", "Escaping charged particles"),
            ("primary_exit_MeV", "Primary exit kinetic energy [MeV]"),
            ("compton", "Compton electrons ≥100 keV"),
        ],
    ):
        values = [r[metric] for _, r in variants]
        ax.bar(
            range(4),
            [v["mean"] for v in values],
            yerr=[v["sem"] for v in values],
            color=["#2278b5", "#39a05d", "#95b74e", "#df7d20"],
            capsize=3,
        )
        ax.set_xticks(range(4), [v[0] for v in variants], fontsize=9)
        ax.set_title(label)
        ax.set_ylabel(
            "Mean / incident particle"
            + (" (zero for stopped primaries)" if metric == "primary_exit_MeV" else "")
        )
        ax.set_ylim(0, max(v["mean"] for v in values) * 1.2)
        for i, v in enumerate(values):
            ax.text(i, v["mean"] * 1.03, f'{v["mean"]:.3f}', ha="center", fontsize=10)
    save(
        fig,
        "Same-material electron cascade: stopping and step refinement",
        "20 MeV electrons in 30 mm Si; 100 keV diagnostic thresholds, 50,000 trials/setting.\nWithout scattering: charged escape improves from 6.254 (ae02) to 0.986, versus G4 1.002.\n"
        "G4 matched processes omit photoelectric absorption and annihilation for this diagnostic only. Error bars: Monte Carlo standard errors.\n"
        "Default bounds: 2% mean energy loss, 0.04 rad² projected variance. Tighter: 1%, 0.01 rad². Residual discretisation bias remains.",
        footer="Controlled homogeneous slabs · no detector geometry · inclusive detector plots retain default G4",
    )

    fig, axes = plt.subplots(1, 3, figsize=(16, 8))
    for ax, energy in zip(axes[:2], [1, 20]):
        vals = [
            slab(11, energy, 0.3, "full", backend)["primary_exit_sin2"]
            for backend in ["fatras", "g4"]
        ]
        ax.bar(
            ["Fatras", "G4"],
            [v["mean"] for v in vals],
            yerr=[v["sem"] for v in vals],
            color=colors[1:],
            capsize=3,
        )
        ax.set_title(f"{energy} MeV electron, 0.3 mm Si")
        ax.set_ylabel("Mean sin²(exit angle), zero for stopped primaries")
    vals = [
        slab(22, 20, 30, profile, backend)["compton"]
        for backend, profile in [
            ("fatras", "full"),
            ("g4", "transport"),
            ("g4", "full"),
        ]
    ]
    axes[2].bar(
        range(3),
        [v["mean"] for v in vals],
        yerr=[v["sem"] for v in vals],
        color=[colors[1], "#eba65e", colors[2]],
        capsize=3,
    )
    axes[2].set_xticks(range(3), ["Fatras", "G4 matched\nprocesses", "G4 full"])
    axes[2].set_title("20 MeV photon, 30 mm Si")
    axes[2].set_ylabel("Compton electrons ≥100 keV / incident photon")
    save(
        fig,
        "Angular check and remaining cascade physics",
        "Thin-slab angular moments test the local scattering law independently of detector occupancy.\n"
        "The matched-process/full-G4 contrast retains the missing photoelectric and annihilation effects; it is not a fitted correction.\n"
        "Gaussian diffusion does not validate Rutherford tails or all low-energy/high-Z materials.",
        footer="Controlled slabs · 50,000 incident particles per setting · same 100 keV diagnostic thresholds",
    )

    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    variants = [
        ("ae02", before),
        ("Core fix only", d["ablations"]["core-only"]["mean"]),
        (
            "Adaptive/scattering\nwithout new birth columns",
            d["ablations"]["no-new-birth"]["mean"],
        ),
        ("Full change", cur),
    ]
    for ax, metric, title in zip(
        axes,
        ["ID_totals", "ID_process"],
        ["All secondary ID hits", "Ionisation-carrier ID hits"],
    ):
        key = "secondary" if metric == "ID_totals" else "5"
        vals = [m[metric][key] / 1000 for _, m in variants]
        ax.bar(range(4), vals, color=["#888", "#aaa", "#39a05d", colors[1]])
        ax.set_xticks(range(4), [n for n, _ in variants], rotation=12, fontsize=9)
        ax.set_title(title)
        ax.set_ylabel("Thousands / event")
        for i, v in enumerate(vals):
            ax.text(i, v + 0.3, f"{v:.2f}", ha="center")
    save(
        fig,
        "Why corrected birth transport reduces the hit count",
        "Core-only uses ae02 physics with the navigation-cache fix. The other diagnostic omits only new ionisation/Compton-electron birth columns.\n"
        "They isolate implementation effects on the same events; neither diagnostic is a replacement baseline.\n"
        f'Propagation failures / three events: ae02 {d["failures"]["control-0"]}; core-only {d["failures"]["core-only"]}; full change {d["failures"]["current-0"]}.',
    )
print(a.output)
