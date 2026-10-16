"""PDF: identical-material response, cascade defects and process attribution."""

import argparse, json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--preview", action="store_true")
a = p.parse_args()
records = json.loads((a.work / "analysis.json").read_text())["records"]
plt.rcParams.update(
    {
        "font.size": 11,
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
blue = "#2379b4"
orange = "#d47d22"
page = 0


def get(
    metric,
    backend="fatras",
    slices=1000,
    mode="cascade",
    profile="common",
    pdg=22,
    e=20,
    t=30,
    mat="G4_Si",
):
    r = max(
        (
            r
            for r in records
            if r["backend"] == backend
            and r["slices"] == slices
            and r["mode"] == mode
            and r["profile"] == profile
            and r["pdg"] == pdg
            and r["energy_MeV"] == e
            and r["thickness_mm"] == t
            and r["material"] == mat
        ),
        key=lambda r: r["n"],
    )
    v = r["metrics"][metric]
    return v["mean"], v["sem"]


def g4(metric, **kw):
    return get(metric, backend="g4", slices=1, **kw)


def curve(ax, metric, slices, **kw):
    vals = np.array([get(metric, slices=n, **kw) for n in slices])
    ax.errorbar(
        slices,
        vals[:, 0],
        yerr=vals[:, 1],
        fmt="o-",
        color=blue,
        capsize=3,
        label="Fatras",
    )
    ref, err = g4(metric, **kw)
    ax.axhline(ref, color=orange, label="G4")
    ax.axhspan(ref - err, ref + err, color=orange, alpha=0.2)
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(slices, [str(n) for n in slices])
    ax.set_xlabel("Fatras material slices")
    ax.grid(axis="y", alpha=0.2)
    return vals, ref


def save(pdf, fig, title, note):
    global page
    page += 1
    fig.suptitle(title, fontsize=19, y=0.97)
    fig.subplots_adjust(
        left=0.08, right=0.97, top=0.82, bottom=0.25, wspace=0.34, hspace=0.55
    )
    fig.text(0.07, 0.135, note, fontsize=11, va="top")
    fig.text(
        0.025,
        0.025,
        "Identical Si/Cu material inputs · zero field · diagnostic yields above 100 keV · error bars: 1 standard error · no ODD hit prediction",
        fontsize=9,
    )
    pdf.savefig(fig)
    if a.preview:
        fig.savefig(a.output.with_name(a.output.stem + f"-{page}.png"), dpi=120)
    plt.close(fig)


with PdfPages(a.output) as pdf:
    fig, axes = plt.subplots(1, 3, figsize=(15, 8))
    for ax, metric, title, kw in [
        (
            axes[0],
            "compton",
            "1 MeV photons: Compton electrons",
            dict(mode="primary", e=1),
        ),
        (axes[1], "brems", "20 MeV photons: cascade brems photons", {}),
        (axes[2], "escape_charged", "20 MeV photons: escaping charged particles", {}),
    ]:
        vals, ref = curve(ax, metric, [1, 20, 100, 1000], **kw)
        ax.set_title(title, fontsize=12)
        ax.set_ylabel("Mean per incident photon")
        ax.legend(fontsize=9)
        ax.set_ylim(0, max(ref, vals[:, 0].max()) * 1.22)
        ax.annotate(
            f"{vals[0,0]:.3f}",
            (1, vals[0, 0]),
            xytext=(4, 9),
            textcoords="offset points",
        )
        ax.annotate(
            f"G4 {ref:.3f}",
            (1000, ref),
            xytext=(-8, 12),
            textcoords="offset points",
            ha="right",
            color=orange,
        )
    save(
        pdf,
        fig,
        "Same 30 mm silicon slab: cascade treatment causes large errors",
        "Common processes only; multiple scattering, photoelectric absorption and annihilation disabled.\n"
        "Coarse slabs lose cascades and let too many daughters escape. Fine slices largely restore the common-process response.\n"
        "100,000 trials per selected point; 20-slice scan points use 10,000. These are bulk-slab stress tests, not detector occupancies.",
    )

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    for ax, metric, title, pdg, energies in [
        (
            axes[0, 0],
            "ionisation",
            "Primary electron: delta-electron yield",
            11,
            [1, 5, 20],
        ),
        (axes[0, 1], "brems", "Primary electron: brems yield", 11, [1, 5, 20]),
        (
            axes[1, 0],
            "conversion",
            "Primary photon: conversion-daughter yield",
            22,
            [5, 20],
        ),
    ]:
        for mat, col, shift in [("G4_Si", blue, -0.04), ("G4_Cu", orange, 0.04)]:
            vals = []
            errs = []
            for e in energies:
                kw = dict(mode="primary", pdg=pdg, e=e, mat=mat)
                try:
                    f, fe = get(metric, slices=1000, **kw)
                except ValueError:
                    f, fe = get(metric, slices=100, **kw)
                g, ge = g4(metric, **kw)
                vals.append(f / g)
                errs.append(np.hypot(fe / g, f * ge / g**2))
            ax.errorbar(
                np.array(energies) * (1 + shift),
                vals,
                yerr=errs,
                fmt="o-",
                color=col,
                label=mat.removeprefix("G4_"),
                capsize=3,
            )
        ax.axhline(1, color="black", lw=1)
        ax.set_xscale("log")
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xticks(energies, [str(e) for e in energies])
        ax.set_ylim(0.75, 1.15)
        ax.set_title(title)
        ax.set_xlabel("Incident kinetic energy [MeV]")
        ax.set_ylabel("Fatras / G4")
        ax.legend()
        ax.grid(axis="y", alpha=0.2)
    curve(
        axes[1, 1], "primary_exit_MeV", [1, 20, 100, 1000], mode="primary", pdg=11, e=20
    )
    axes[1, 1].set_title("20 MeV electrons in Si: mean primary exit energy")
    axes[1, 1].set_ylabel("MeV, zero if stopped")
    axes[1, 1].legend()
    save(
        pdf,
        fig,
        "Primary response: smaller residual kernel differences remain",
        "30 mm slabs; common processes; daughters counted but not transported. Native ratios use 100–1000 slices.\n"
        "Ionisation and brems yields are much closer than the ODD discrepancy. Cu conversion remains about 10% low at 5 MeV.\n"
        "Selected points: 100,000 trials; other scan points: 10,000. Mean loss and fluctuations remain model differences.",
    )

    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    profiles = ["common", "photoelectric", "annihilation", "extended", "full"]
    labels = ["Common", "+ photoelectric", "+ annihilation", "+ both", "+ both + MSC"]
    for ax, pdg, name in [
        (axes[0], 22, "20 MeV photon beam"),
        (axes[1], 11, "20 MeV electron beam"),
    ]:
        vals = np.array([g4("compton", profile=p, pdg=pdg) for p in profiles])
        ax.bar(
            range(5), vals[:, 0], yerr=vals[:, 1], color=orange, capsize=4, label="G4"
        )
        for x, prof in [(0, "common"), (4, "full")]:
            v, e = get("compton", profile=prof, pdg=pdg)
            ax.errorbar(
                x,
                v,
                yerr=e,
                fmt="o",
                color=blue,
                capsize=4,
                label="Fatras, 1000 slices" if x == 0 else None,
            )
        ax.set_xticks(range(5), labels, rotation=20, ha="right")
        ax.set_title(name + " through 30 mm Si")
        ax.set_ylabel("Compton electrons per incident particle")
        ax.legend(loc="upper left", fontsize=10)
        ax.set_ylim(0, vals[:, 0].max() * 1.35)
    save(
        pdf,
        fig,
        "Missing annihilation and charged scattering both affect cascades",
        "100,000 trials per setting. Each G4 column enables the named processes relative to the common-process control.\n"
        "Annihilation raises the photon-beam Compton yield by about 31%; photoelectric alone has little effect on that yield.\n"
        "Multiple scattering changes path lengths and stopping. These controlled increments cannot be added to ODD hit deficits.",
    )

    fig, axes = plt.subplots(1, 3, figsize=(15, 8))
    for ax, metric, title in [
        (axes[0], "primary_exit_MeV", "Mean primary exit energy [MeV]"),
        (axes[1], "escape_charged", "Escaping charged particles"),
        (axes[2], "compton", "Compton electrons produced"),
    ]:
        curve(ax, metric, [1, 20, 100, 1000, 10000], profile="full", pdg=11)
        ax.set_title(title, fontsize=12)
        ax.set_ylabel("Mean per incident electron")
        ax.tick_params(axis="x", rotation=30)
        ax.legend(fontsize=9)
    save(
        pdf,
        fig,
        "Subdivision is a diagnostic — not a production solution",
        "20 MeV electrons, 30 mm Si, multiple scattering enabled. 100/1000 slices: 100,000 trials; 10,000 slices: 20,000 trials.\n"
        "Primary exit energy moves through the G4 result as subdivision increases. A good value at one slice count is not convergence.\n"
        "The electron scattering width contains a logarithmic thickness term: repeated independent thin kicks change its total variance.",
    )
print(a.output)
