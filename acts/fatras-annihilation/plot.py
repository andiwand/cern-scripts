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
attrib = json.loads((a.work / "attribution.json").read_text())
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
        "Native positron annihilation: inclusive hits and CPU",
        f'Secondary ID deficit: {gap(before,"ID"):.2f}% → {gap(cur,"ID"):.2f}%; pixel deficit: {gap(before,"pixel"):.2f}% → {gap(cur,"pixel"):.2f}%.\n'
        f'Matched CPU medians: Fatras 120acbe04e {d["timings"]["control"]["median"]:.2f} s; changed {cpu[1]:.2f} s (three serial repeats each).\n'
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

    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    variants = [("Annihilation off", before), ("Annihilation on", cur)]
    for i, (label, m) in enumerate(variants):
        axes[0].bar(
            np.arange(2) + (i - 0.5) * 0.35,
            [m["ID_totals"]["secondary"] / 1000, m["ID_process"]["6"] / 1000],
            width=0.35,
            label=label,
            color=["#888", colors[1]][i],
        )
    axes[0].set_xticks([0, 1], ["All secondary ID", "Other-carrier ID"])
    axes[0].set_ylabel("Thousands of hits / event")
    axes[0].legend()
    axes[0].set_title("Same-event process toggle")
    for i, name in enumerate(["Current", "Geant4"]):
        m = attrib[name]["mean_hits"]
        axes[1].bar(
            np.arange(2) + (i - 0.5) * 0.35,
            [
                sum(v for k, v in m.items() if k.startswith(scope + ":annihilation:"))
                for scope in ["pixel", "ID"]
            ],
            width=0.35,
            label="Fatras" if name == "Current" else name,
            color=colors[i + 1],
        )
    axes[1].set_xticks([0, 1], ["Pixel", "ID"])
    axes[1].set_ylabel("Secondary hits / event")
    axes[1].set_title("Hits with an annihilation photon ancestor")
    axes[1].legend()
    save(
        fig,
        "Which hits does annihilation supply?",
        "Annihilation off replays the preceding implementation exactly. The toggle also changes subsequent random draws.\n"
        "Lineage counts measure actual descendant hits; they are not the net change in the event.\n"
        "Annihilation photons are identified by photon / Other / positron-parent truth; unknown ancestry is retained separately.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    procs = ["1", "2", "4", "5", "6"]
    delta = [g4["ID_process"].get(k, 0) - cur["ID_process"].get(k, 0) for k in procs]
    axes[0].bar(
        range(5),
        np.array(delta) / 1000,
        color=[colors[2] if x > 0 else colors[1] for x in delta],
    )
    axes[0].axhline(0, color="black", lw=0.8)
    axes[0].set_xticks(
        range(5), ["Decay", "Conversion", "Nuclear", "Ionisation", "Other"], rotation=15
    )
    axes[0].set_title("Residual secondary ID difference")
    axes[0].set_ylabel("G4 minus Fatras, thousands / event")
    obs = attrib["g4_observer"]["process_location_energy"]
    labels = [("eIoni", "hIoni", "muIoni", "ionIoni"), ("compt",), ("phot",)]
    bottom = np.zeros(3)
    for site, c in [("sensor birth", "#df7d20"), ("other birth", "#eebf80")]:
        vals = (
            np.array(
                [
                    sum(
                        v
                        for k, v in obs.items()
                        if any(
                            k.startswith(proc + ":" + site + ":") for proc in processes
                        )
                    )
                    for processes in labels
                ]
            )
            / 1000
        )
        axes[1].bar(range(3), vals, bottom=bottom, label=site, color=c)
        bottom += vals
    axes[1].set_xticks(range(3), ["Ionisation", "Compton", "Photoelectric"])
    axes[1].set_ylabel("G4 secondary ID hits, thousands / event")
    axes[1].set_title("G4 carrier birth location")
    axes[1].legend()
    below = sum(
        v
        for k, v in g4["ID_acceptance_partition"].items()
        if not k.endswith(":above both")
    )
    save(
        fig,
        "Residual attribution: production, transport and material locality",
        f"G4 has {below:,.0f} secondary ID hits below the Fatras charged or ionisation-production acceptance (disjoint diagnostic bins).\n"
        "Birth location is a measured association, not a causal material correction; it overlaps energy/process partitions.\n"
        "The bars do not establish a unique physics/material split. Sensor placement remains deferred; all summary hits are retained.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    groups = ["electron or positron", "other charged"]
    for i, name in enumerate(["Current", "Geant4"]):
        flow = attrib[name]["mean_flow"]
        axes[0].bar(
            np.arange(2) + (i - 0.5) * 0.35,
            [
                flow.get(f"ionisation particles:{g}:at least 2 MeV", 0) / 1000
                for g in groups
            ],
            width=0.35,
            color=colors[i + 1],
            label="Fatras" if name == "Current" else name,
        )
    axes[0].set_xticks(
        [0, 1], ["Electron/positron parent", "Other charged parent"], rotation=10
    )
    axes[0].set_ylabel("Retained electrons ≥2 MeV, thousands / event")
    axes[0].set_title("Ionisation source at a common diagnostic energy")
    axes[0].legend()
    origins = ["eBrem", "annihil", "Decay", "primary", "nuclear"]
    current = attrib["Current"]["mean_flow"]
    g4origins = {k: 0 for k in origins}
    for key, v in attrib["g4_observer"]["compton_parent_location"].items():
        proc = key.split(":")[0]
        g4origins[proc if proc in origins else "nuclear"] += v
    for i, values in enumerate(
        [
            [current.get("Compton hits by photon source:" + k, 0) for k in origins],
            [g4origins[k] for k in origins],
        ]
    ):
        axes[1].bar(
            np.arange(5) + (i - 0.5) * 0.35,
            np.array(values) / 1000,
            width=0.35,
            color=colors[i + 1],
            label=["Fatras", "G4"][i],
        )
    axes[1].set_xticks(
        range(5),
        ["Brems", "Annihilation", "Decay", "Primary", "Hadronic/capture"],
        rotation=20,
    )
    axes[1].set_ylabel("All Compton-carrier ID hits, thousands / event")
    axes[1].set_title("Which photon sources feed Compton hits?")
    axes[1].legend()
    save(
        fig,
        "Source production is only part of the hit deficit",
        "The left diagnostic counts sources above 2 MeV; it does not select any inclusive summary hits.\n"
        "Default G4 electron production cuts vary by material (Si 0.423 MeV, Cu 1.034 MeV); raw ≥100 keV source counts are not matched.\n"
        "Right: native Compton continuation photons are traced back to their source; G4 uses the observed parent creator.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 8))
    for ax, pdg, energy, thickness in zip(
        axes, [22, -11, -11], [20, 1, 20], [30, 10, 30]
    ):
        variants = [
            ("Fatras off", "fatras", "transport"),
            ("Fatras on", "fatras", "annihilation-transport"),
            ("G4 off", "g4", "transport"),
            ("G4 on", "g4", "annihilation-transport"),
            ("G4 full", "g4", "full"),
        ]
        vals = [
            d["slabs"][f"{pdg}-{energy}-{thickness}-{profile}-{backend}"]["metrics"][
                "compton"
            ]
            for _, backend, profile in variants
        ]
        ax.bar(
            range(5),
            [v["mean"] for v in vals],
            yerr=[v["sem"] for v in vals],
            capsize=3,
            color=["#888", colors[1], "#aaa", "#eebf80", colors[2]],
        )
        ax.set_xticks(range(5), [v[0] for v in variants], rotation=25, fontsize=9)
        ax.set_title(
            f"{energy} MeV {'photon' if pdg==22 else 'positron'}, {thickness} mm Si"
        )
        ax.set_ylabel("Compton electrons ≥100 keV / primary")
    save(
        fig,
        "Same-material cascade response isolates annihilation",
        "20,000 trials per setting; error bars are Monte Carlo standard errors. All profiles include charged scattering.\n"
        "Only this diagnostic disables processes / matches 100 keV thresholds. Inclusive ODD uses default G4.\n"
        "Residual positron backscattering/stopping and photon-spectrum differences remain; no occupancy correction is fitted.",
        footer="Homogeneous controlled slabs · no detector geometry",
    )
    import csv

    kernel = list(csv.DictReader((a.work / "kernel.csv").open()))
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    energy = [float(r["kinetic_MeV"]) for r in kernel]
    axes[0].semilogx(
        energy,
        [1e6 * (float(r["native_mm2"]) / float(r["g4_mm2"]) - 1) for r in kernel],
        "o-",
    )
    axes[0].set_xlabel("Positron kinetic energy [MeV]")
    axes[0].set_ylabel("Native / G4 cross section − 1 [ppm]")
    axes[0].set_title("Total cross section per electron")
    for key, label, c in [
        ("native_mean_asymmetry", "Native analytic", colors[1]),
        ("g4_mean_asymmetry", "Installed G4", colors[2]),
    ]:
        axes[1].semilogx(
            energy, [float(r[key]) for r in kernel], "o-", label=label, color=c
        )
    axes[1].legend()
    axes[1].set_xlabel("Positron kinetic energy [MeV]")
    axes[1].set_ylabel("Mean |E₁ − E₂| / (E₁ + E₂)")
    axes[1].set_title("In-flight photon energy sharing")
    save(
        fig,
        "Direct model check: same rate, different in-flight spectrum",
        "Cross sections agree within 0.13 ppm. At rest: two isotropic back-to-back 511 keV photons.\n"
        "Native sampling follows the analytic differential prescription in the G4 Physics Reference Manual; installed G4 11.3.2 uses\n"
        "an isotropic CM construction here. This measured high-energy difference is retained explicitly, not tuned to detector hits.",
        footer="Direct native / installed G4 kernel comparison · 100,000 final states per energy · no transport",
    )
print(a.output)
