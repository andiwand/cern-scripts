#!/usr/bin/env python3
"""ODD simulation-hit validation, following the synthetic fast-sim plot suite.

Uses identical event IDs, per-event normalization and event-level uncertainties.
Particle plots require charged particles with pixel hits, pT>100 MeV, |eta|<4.
Raw and common-transport-acceptance hit rates are kept separate.
"""
import argparse, hashlib, json, re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LogNorm

BAR = [
    "particle_id_pv",
    "particle_id_sv",
    "particle_id_part",
    "particle_id_gen",
    "particle_id_subpart",
]
STYLE = {
    "geant4": ("#2563a6", "Geant4 FTFP_BERT"),
    "fatras-em": ("#888888", "Fatras EM only"),
    "fatras": ("#d55e00", "Fatras + decays + Si table"),
}
PROC = [
    "undefined",
    "decay",
    "conversion",
    "bremsstrahlung",
    "nuclear",
    "ionisation",
    "other",
]
plt.rcParams.update(
    {
        "font.size": 9,
        "axes.grid": True,
        "grid.alpha": 0.2,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def perigee(vx, vy, vz, px, py, pz, q):
    # Same uniform-field helix definition as synthetic-sim-validation/sample.py.
    phi = np.arctan2(py, px)
    pt = np.hypot(px, py)
    q = np.sign(q)
    rho = pt * 1000 / (0.299792458 * 2)
    cx = vx + q * rho * np.sin(phi)
    cy = vy - q * rho * np.cos(phi)
    rc = np.hypot(cx, cy)
    d0 = q * (rho - rc)
    with np.errstate(divide="ignore", invalid="ignore"):
        angle = 2 * np.arcsin(
            np.sqrt(np.clip((vx * vx + vy * vy - d0 * d0) / (4 * rc * rho), 0, 1))
        )
        z0 = vz - np.sign(vx * np.cos(phi) + vy * np.sin(phi)) * angle * rho * pz / pt
    return phi, d0, z0


def load(folder, events, cache):
    paths = [
        folder / f"event{e:09d}-{stem}.csv"
        for e in range(events)
        for stem in ("particles_simulated", "hits")
    ]
    signature = hashlib.sha256(
        json.dumps(
            [(str(f.resolve()), f.stat().st_size, f.stat().st_mtime_ns) for f in paths]
        ).encode()
    ).hexdigest()
    if cache.exists():
        with np.load(cache) as saved:
            if "signature" in saved and str(saved["signature"]) == signature:
                return dict(saved)
    parts = {}
    stats = []

    def add(k, v):
        parts.setdefault(k, []).append(np.asarray(v))

    for event in range(events):
        stem = f"event{event:09d}"
        particles = pd.read_csv(folder / f"{stem}-particles_simulated.csv")
        hits = pd.read_csv(folder / f"{stem}-hits.csv", dtype={"geometry_id": "uint64"})
        ids = pd.MultiIndex.from_frame(particles[BAR])
        assert ids.is_unique
        where = ids.get_indexer(pd.MultiIndex.from_frame(hits[BAR]))
        if (where < 0).any():
            raise ValueError(f"{folder}: unmatched truth links {sum(where<0)}")
        vol = hits.geometry_id.to_numpy() >> np.uint64(56)
        layer = (hits.geometry_id.to_numpy() >> np.uint64(36)) & np.uint64(4095)
        pixel = np.isin(vol, [16, 17, 18])
        hp = np.sqrt(
            hits.tpx.to_numpy() ** 2
            + hits.tpy.to_numpy() ** 2
            + hits.tpz.to_numpy() ** 2
        )
        hpt = np.hypot(hits.tpx.to_numpy(), hits.tpy.to_numpy())
        hprimary = hits.particle_id_gen.to_numpy() == 0
        common = (hp >= 0.1) & (hpt >= 0.05)
        proc = particles.process.to_numpy()[where].astype(np.int8)
        # All tracker hits retain layer IDs and event ID; detailed coordinates only pixels.
        for k, v in {
            "all_event": np.full(len(hits), event, np.int16),
            "all_layer": vol * 100 + layer,
            "all_primary": hprimary,
            "all_common": common,
            "all_process": proc,
        }.items():
            add(k, v)
        for k, v in {
            "hit_r": np.hypot(hits.tx.to_numpy(), hits.ty.to_numpy()),
            "hit_z": hits.tz.to_numpy(),
            "hit_phi": np.arctan2(hits.ty.to_numpy(), hits.tx.to_numpy()),
            "hit_t": hits.tt.to_numpy() / 299.792458,
            "hit_p": hp,
            "hit_pt": hpt,
            "hit_primary": hprimary,
            "hit_common": common,
            "hit_process": proc,
            "hit_event": np.full(len(hits), event, np.int16),
        }.items():
            add(
                k,
                (
                    v[pixel].astype(np.float32)
                    if k in ("hit_r", "hit_z", "hit_phi", "hit_t", "hit_p", "hit_pt")
                    else v[pixel]
                ),
            )
        counts = np.bincount(where[pixel], minlength=len(particles))
        pt = np.hypot(particles.px.to_numpy(), particles.py.to_numpy())
        with np.errstate(divide="ignore", invalid="ignore"):
            eta = np.arcsinh(particles.pz.to_numpy() / pt)
        select = (
            (counts > 0)
            & (np.abs(particles.q.to_numpy()) > 0.5)
            & (pt > 0.1)
            & (np.abs(eta) < 4)
        )
        pp = particles.loc[select]
        nhit = counts[select]
        phi, d0, z0 = perigee(
            *(pp[c].to_numpy() for c in ["vx", "vy", "vz", "px", "py", "pz", "q"])
        )
        for k, v in {
            "pt": pt[select],
            "eta": eta[select],
            "phi": phi,
            "d0": np.abs(d0),
            "z0": z0,
            "prod_r": np.hypot(pp.vx.to_numpy(), pp.vy.to_numpy()),
            "prod_z": pp.vz.to_numpy(),
            "num_hits": nhit,
            "primary": pp.particle_id_gen.to_numpy() == 0,
            "process": pp.process.to_numpy().astype(np.int8),
            "pdg": pp.particle_type.to_numpy(),
            "event": np.full(len(pp), event, np.int16),
        }.items():
            add(
                k,
                (
                    v.astype(np.float32)
                    if k in ("pt", "eta", "phi", "d0", "z0", "prod_r", "prod_z")
                    else v
                ),
            )
        stats.append(
            {
                "truth_by_process": np.bincount(
                    particles.process.to_numpy(), minlength=7
                ).tolist(),
                "event": event,
                "particles_written": len(particles),
                "tracker_hits": len(hits),
                "pixel_hits": int(pixel.sum()),
                "pixel_primary_hits": int((pixel & hprimary).sum()),
                "pixel_secondary_hits": int((pixel & ~hprimary).sum()),
                "pixel_common_primary_hits": int((pixel & common & hprimary).sum()),
                "pixel_common_secondary_hits": int((pixel & common & ~hprimary).sum()),
                "pixel_hits_by_process": np.bincount(proc[pixel], minlength=7).tolist(),
                "pixel_common_hits_by_process": np.bincount(
                    proc[pixel & common], minlength=7
                ).tolist(),
            }
        )
        print(folder.name, event, len(hits), len(pp), flush=True)
    out = {k: np.concatenate(v) for k, v in parts.items()}
    out["events"] = np.array(events)
    out["signature"] = np.array(signature)
    np.savez_compressed(cache, **out)
    cache.with_suffix(".json").write_text(json.dumps(stats, indent=2) + "\n")
    return out


def hist(d, key, bins, mask=None):
    evkey = (
        "hit_event"
        if key.startswith("hit_")
        else "all_event" if key.startswith("all_") else "event"
    )
    if mask is None:
        mask = np.ones(len(d[key]), dtype=bool)
    return np.array(
        [
            np.histogram(d[key][mask & (d[evkey] == e)], bins)[0]
            for e in range(int(d["events"]))
        ],
        float,
    )


def panel(ax, rx, samples, key, bins, label, mask_fn=None, logx=False, logy=False):
    matrices = {
        k: hist(d, key, bins, mask_fn(d) if mask_fn else None)
        for k, d in samples.items()
    }
    widths = np.diff(bins)
    centres = (bins[:-1] + bins[1:]) / 2
    ref = matrices["geant4"]
    refmean = ref.mean(axis=0)
    ratio_max = 2.0
    for k, h in matrices.items():
        color, name = STYLE[k]
        mean = h.mean(axis=0)
        sem = h.std(axis=0, ddof=1) / np.sqrt(len(h))
        ax.stairs(mean / widths, bins, label=name, color=color, lw=1.3)
        ax.fill_between(
            centres,
            np.maximum(0, mean - sem) / widths,
            (mean + sem) / widths,
            color=color,
            alpha=0.15,
            step="mid",
        )
        if k != "geant4":
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(refmean > 0, mean / refmean, np.nan)
                # Paired event delta-method uncertainty, including input correlations.
                err = (
                    np.std(h - ratio * ref, axis=0, ddof=1) / np.sqrt(len(h)) / refmean
                )
            if np.isfinite(ratio).any():
                ratio_max = max(ratio_max, float(np.nanmax(ratio)) * 1.1)
            rx.stairs(ratio, bins, color=color, lw=1.2)
            rx.fill_between(
                centres, ratio - err, ratio + err, color=color, alpha=0.15, step="mid"
            )
    if logy:
        ax.set_yscale("log")
        # A one-entry bin can have mean-SEM ~1e-17 from roundoff. Do not let
        # that uncertainty edge set the log-axis range and flatten the data.
        densities = np.concatenate([h.mean(axis=0) / widths for h in matrices.values()])
        positive = densities[densities > 0]
        if len(positive):
            ax.set_ylim(bottom=positive.min() / 3)
    if logx:
        ax.set_xscale("log")
        rx.set_xscale("log")
    ax.set_ylabel("entries / event / axis unit")
    ax.legend(fontsize=7)
    rx.axhline(1, color="black", lw=0.8)
    rx.set_ylabel("Fatras / G4", fontsize=8)
    rx.set_xlabel(label)
    rx.set_ylim(0, ratio_max)
    ax.tick_params(labelbottom=False)


def figure(rows, cols, title):
    fig, axes = plt.subplots(
        2 * rows,
        cols,
        figsize=(4.5 * cols, 3.65 * rows),
        squeeze=False,
        gridspec_kw={"height_ratios": [3, 1] * rows},
    )
    fig.suptitle(title, fontsize=13, y=0.995)
    return fig, axes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--geant4", type=Path)
    p.add_argument("--fatras", type=Path)
    p.add_argument("--em", "--baseline", dest="em", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--events", type=int, default=20)
    p.add_argument("--coverage", type=Path)
    p.add_argument(
        "--cached",
        action="store_true",
        help="Replot archived arrays without raw CSV files",
    )
    p.add_argument(
        "--allow-different-revisions",
        action="store_true",
        help="Reuse a reference from an earlier ACTS revision; geometry and inputs must still match",
    )
    p.add_argument(
        "--allow-material-map-change",
        action="store_true",
        help="Explicit material-map correction study; all other geometry/input checks remain",
    )
    p.add_argument("--baseline-label")
    p.add_argument("--fatras-label")
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    config_file = a.output / "plot-config.json"
    config = (
        json.loads(config_file.read_text()) if a.cached and config_file.exists() else {}
    )
    for key, label in [("fatras-em", a.baseline_label), ("fatras", a.fatras_label)]:
        label = label or config.get(key, STYLE[key][1])
        STYLE[key] = (STYLE[key][0], label)
        config[key] = label
    config["allow_different_revisions"] = a.allow_different_revisions or config.get(
        "allow_different_revisions", False
    )
    config["allow_material_map_change"] = a.allow_material_map_change or config.get(
        "allow_material_map_change", False
    )
    config_file.write_text(json.dumps(config, indent=2) + "\n")
    folders = {"geant4": a.geant4, "fatras-em": a.em, "fatras": a.fatras}
    if a.events < 2:
        p.error("At least two events are required for event uncertainties")
    if a.cached:
        samples = {k: dict(np.load(a.output / f"{k}-{a.events}.npz")) for k in folders}
        assert all(int(d["events"]) == a.events for d in samples.values())
    else:
        if any(v is None for v in folders.values()):
            p.error("Supply all three sample directories, or --cached")
        metadata = {
            k: json.loads((v / "metadata.json").read_text()) for k, v in folders.items()
        }
        keys = [
            "acts_revision",
            "odd_revision",
            "material_map_sha256",
            "field_T",
            "world_bounds",
            "events",
            "seed",
        ]
        if a.allow_material_map_change:
            keys.remove("material_map_sha256")
        if a.allow_different_revisions:
            keys.remove("acts_revision")
        for key in keys:
            assert all(
                m[key] == metadata["geant4"][key] for m in metadata.values()
            ), f"Mismatched {key}"
        selections = [
            json.loads((Path(m["input"]) / "selection.json").read_text())
            for m in metadata.values()
        ]
        assert all(
            s == selections[0] for s in selections
        ), "Mismatched generator inputs"
        for m in metadata.values():
            for filename, sha in selections[0]["sha256"].items():
                assert (
                    hashlib.sha256(
                        (Path(m["input"]) / filename).read_bytes()
                    ).hexdigest()
                    == sha
                )
        (a.output / "input-selection.json").write_text(
            json.dumps(selections[0], indent=2) + "\n"
        )
        (a.output / "run-metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n"
        )
        samples = {
            k: load(v, a.events, a.output / f"{k}-{a.events}.npz")
            for k, v in folders.items()
        }
    book = PdfPages(a.output / "odd_geant4_vs_fatras.pdf")
    subtitle = (
        f"{a.events} matched ttbar + PU200 events; ODD pixels (volumes 16–18); Bz = 2 T"
    )

    def save(
        fig,
        stem,
        caption="Per-event rates; bands: event SEM. Ratio bands use paired events; empty G4 bins omitted.",
    ):
        fig.text(
            0.5,
            0.015,
            (
                subtitle.replace("ODD pixels (volumes 16–18)", "ODD pixels + strips")
                if stem in ("tracker_layers", "material_coverage")
                else subtitle
            )
            + "\n"
            + caption,
            ha="center",
            fontsize=8,
        )
        fig.tight_layout(rect=(0, 0.07, 1, 0.96))
        fig.savefig(a.output / (stem + ".pdf"))
        book.savefig(fig)
        if stem in [
            "components_common",
            "secondary_kinematics",
            "processes",
            "occupancy_rz",
        ]:
            fig.savefig(a.output / (stem + ".png"), dpi=130)
        plt.close(fig)

    for common in (False, True):
        fig, ax = figure(
            2,
            2,
            "Pixel hit occupancy by component"
            + (
                " — common momentum acceptance" if common else " — all recorded momenta"
            ),
        )
        for row, primary in enumerate([True, False]):
            for col, (key, bins, label) in enumerate(
                [
                    ("hit_r", np.array([0, 25, 50, 90, 140, 200.0]), "hit r [mm]"),
                    ("hit_z", np.linspace(-1600, 1600, 41), "hit z [mm]"),
                ]
            ):

                def mask(d, primary=primary, common=common):
                    return (d["hit_primary"] == primary) & (
                        d["hit_common"] if common else True
                    )

                panel(
                    ax[2 * row, col],
                    ax[2 * row + 1, col],
                    samples,
                    key,
                    bins,
                    label,
                    mask,
                    logy=True,
                )
                ax[2 * row, col].set_title(
                    "Generator particles" if primary else "Simulation secondaries"
                )
        save(
            fig,
            "components_common" if common else "components_inclusive",
            (
                "Hit-entry p ≥ 100 MeV, pT ≥ 50 MeV; "
                if common
                else "Includes hits below Fatras transport cuts; "
            )
            + "event-level uncertainty bands; generator-decay daughters count as generator particles.",
        )
    specs = [
        ("eta", np.linspace(-4, 4, 33), "eta", False, False),
        ("pt", np.geomspace(0.1, 30, 33), "production pT [GeV]", True, True),
        ("d0", np.geomspace(0.001, 1000, 37), "|d0| [mm]", True, True),
        ("num_hits", np.arange(0.5, 20.6, 1), "pixel hits / particle", False, True),
        ("prod_r", np.linspace(0, 1200, 49), "production r [mm]", False, True),
        ("prod_z", np.linspace(-4000, 4000, 65), "production z [mm]", False, True),
        ("phi", np.linspace(-np.pi, np.pi, 33), "phi [rad]", False, False),
        ("z0", np.linspace(-1000, 1000, 41), "z0 [mm]", False, True),
    ]
    for primary in [True, False]:
        fig, ax = figure(
            2,
            4,
            ("Generator-particle" if primary else "Secondary")
            + " kinematics — absolute rates",
        )
        for i, (key, bins, label, lx, ly) in enumerate(specs):
            row, col = divmod(i, 4)
            panel(
                ax[2 * row, col],
                ax[2 * row + 1, col],
                samples,
                key,
                bins,
                label,
                lambda d: d["primary"] == primary,
                lx,
                ly,
            )
        save(
            fig,
            "primary_kinematics" if primary else "secondary_kinematics",
            "Charged particles with ≥1 pixel hit, production pT > 100 MeV, |eta| < 4; no shape renormalization.",
        )
    fig, ax = figure(1, 3, "Secondary pixel hits — momentum and arrival time")
    for col, (key, bins, label) in enumerate(
        [
            ("hit_p", np.geomspace(0.0001, 100, 49), "hit-entry p [GeV]"),
            ("hit_pt", np.geomspace(0.0001, 100, 49), "hit-entry pT [GeV]"),
            ("hit_t", np.geomspace(0.01, 10000, 61), "arrival time [ns]"),
        ]
    ):
        panel(
            ax[0, col],
            ax[1, col],
            samples,
            key,
            bins,
            label,
            lambda d: ~d["hit_primary"],
            True,
            True,
        )
    save(
        fig,
        "secondary_hit_spectra",
        "All recorded secondary hits; Fatras charged transport p ≥ 100 MeV, pT ≥ 50 MeV; Geant4 configured time-kill threshold 1000 ns (step-level, not a strict hit cut).",
    )
    # Common colour scale is essential to expose missing occupancy.
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharex=True, sharey=True)
    maps = {}
    for k, d in samples.items():
        maps[k] = (
            np.histogram2d(
                d["hit_z"],
                d["hit_r"],
                [np.linspace(-1600, 1600, 161), np.linspace(0, 200, 81)],
            )[0]
            / a.events
        )
    vmax = max(x.max() for x in maps.values())
    norm = LogNorm(vmin=0.05, vmax=vmax)
    for ax, (k, h) in zip(axes, samples.items()):
        mesh = ax.pcolormesh(
            np.linspace(-1600, 1600, 161),
            np.linspace(0, 200, 81),
            maps[k].T,
            norm=norm,
            cmap="viridis",
            rasterized=True,
        )
        ax.set_title(STYLE[k][1])
        ax.set_xlabel("z [mm]")
        ax.grid(False)
    axes[0].set_ylabel("r [mm]")
    fig.colorbar(
        mesh,
        cax=fig.add_axes([0.25, 0.16, 0.5, 0.035]),
        orientation="horizontal",
        label="hits / event / spatial bin",
    )
    fig.suptitle("Pixel hit occupancy — shared colour scale")
    # Custom layout for shared colourbar.
    fig.subplots_adjust(bottom=0.33, top=0.84, wspace=0.08)
    fig.text(0.5, 0.02, subtitle, ha="center", fontsize=8)
    fig.savefig(a.output / "occupancy_rz.pdf")
    book.savefig(fig)
    fig.savefig(a.output / "occupancy_rz.png", dpi=130)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, common in zip(axes, [False, True]):
        for i, (k, d) in enumerate(samples.items()):
            mask = ~d["hit_primary"] & (d["hit_common"] if common else True)
            h = hist(d, "hit_process", np.arange(-0.5, 7.5, 1), mask)
            ax.bar(
                np.arange(1, 7) + (i - 1) * 0.23,
                h.mean(axis=0)[1:],
                width=0.23,
                yerr=h.std(axis=0, ddof=1)[1:] / np.sqrt(a.events),
                color=STYLE[k][0],
                label=STYLE[k][1],
            )
        ax.set_xticks(np.arange(1, 7), PROC[1:], rotation=25, ha="right")
        ax.set_yscale("log")
        ax.set_ylabel("secondary pixel hits / event")
        ax.set_title(
            "Common hit momentum cuts" if common else "All recorded hit momenta"
        )
        ax.legend(fontsize=7)
    fig.suptitle("Secondary hits by the hit particle’s creation process")
    save(
        fig,
        "processes",
        "Immediate creator process, not the full shower ancestry; zeros have no log-height.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    bins = np.linspace(-4, 4, 17)
    centres = (bins[:-1] + bins[1:]) / 2
    for ax, primary in zip(axes, [True, False]):
        for k, d in samples.items():
            mask = d["primary"] == primary
            nh = np.histogram(d["eta"][mask], bins, weights=d["num_hits"][mask])[0]
            n = np.histogram(d["eta"][mask], bins)[0]
            ax.plot(
                centres,
                np.divide(
                    nh, n, out=np.full_like(nh, np.nan, dtype=float), where=n > 0
                ),
                marker=".",
                label=STYLE[k][1],
                color=STYLE[k][0],
            )
        ax.set_xlabel("production eta")
        ax.set_ylabel("mean pixel hits / selected particle")
        ax.set_title("Generator particles" if primary else "Simulation secondaries")
        ax.legend(fontsize=7)
    fig.suptitle("Pixel hits versus eta")
    save(
        fig,
        "hits_vs_eta",
        "Charged particles with ≥1 pixel hit, production pT > 100 MeV and |eta| < 4; conditional mean.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharex=True, sharey=True)
    maps = {
        k: np.histogram2d(
            d["prod_z"][~d["primary"]],
            d["prod_r"][~d["primary"]],
            [np.linspace(-4000, 4000, 161), np.linspace(0, 1200, 121)],
        )[0]
        / a.events
        for k, d in samples.items()
    }
    norm = LogNorm(vmin=0.05, vmax=max(x.max() for x in maps.values()))
    for ax, k in zip(axes, samples):
        mesh = ax.pcolormesh(
            np.linspace(-4000, 4000, 161),
            np.linspace(0, 1200, 121),
            maps[k].T,
            norm=norm,
            rasterized=True,
            cmap="viridis",
        )
        ax.set_title(STYLE[k][1])
        ax.set_xlabel("production z [mm]")
        ax.grid(False)
    axes[0].set_ylabel("production r [mm]")
    fig.colorbar(
        mesh,
        cax=fig.add_axes([0.25, 0.16, 0.5, 0.035]),
        orientation="horizontal",
        label="selected secondary particles / event / bin",
    )
    fig.suptitle("Production vertices of secondaries with pixel hits")
    fig.subplots_adjust(bottom=0.33, top=0.84, wspace=0.08)
    fig.text(
        0.5,
        0.02,
        subtitle
        + "\nCharged particles; production pT > 100 MeV, |eta| < 4; shared colour scale.",
        ha="center",
        fontsize=8,
    )
    fig.savefig(a.output / "production_rz.pdf")
    book.savefig(fig)
    plt.close(fig)
    # Full silicon tracker cross-check, integrated over actual geometry layer IDs.
    layers = np.unique(samples["geant4"]["all_layer"])
    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    for ax, primary in zip(axes, [True, False]):
        for k, d in samples.items():
            h = (
                np.array(
                    [
                        np.count_nonzero(
                            (d["all_layer"] == layer)
                            & (d["all_primary"] == primary)
                            & d["all_common"]
                        )
                        for layer in layers
                    ]
                )
                / a.events
            )
            ax.plot(np.arange(len(layers)), h, label=STYLE[k][1], color=STYLE[k][0])
            ax.set_yscale("log")
            ax.set_ylabel("hits / event")
            ax.set_title("Generator particles" if primary else "Simulation secondaries")
            ax.legend(fontsize=7)
    axes[-1].set_xticks(
        np.arange(len(layers)),
        [f"{int(x)//100}:{int(x)%100}" for x in layers],
        rotation=90,
        fontsize=6,
    )
    axes[-1].set_xlabel("ACTS volume:layer (pixels and strips)")
    fig.suptitle("Full silicon tracker — hits per layer, common momentum cuts")
    save(
        fig,
        "tracker_layers",
        "Layer counts include pixels and strips; hit-entry p ≥ 100 MeV and pT ≥ 50 MeV.",
    )
    summary = {}
    for k, d in samples.items():
        summary[k] = {
            "events": a.events,
            "pixel_hits_per_event": len(d["hit_r"]) / a.events,
            "pixel_hits_after_1000ns": int((d["hit_t"] > 1000).sum()),
            "primary_pixel_hits_per_event": float(d["hit_primary"].sum() / a.events),
            "secondary_pixel_hits_per_event": float(
                (~d["hit_primary"]).sum() / a.events
            ),
            "common_primary_pixel_hits_per_event": float(
                (d["hit_primary"] & d["hit_common"]).sum() / a.events
            ),
            "common_secondary_pixel_hits_per_event": float(
                (~d["hit_primary"] & d["hit_common"]).sum() / a.events
            ),
            "common_secondary_process_hits_per_event": dict(
                zip(
                    PROC,
                    (
                        np.bincount(
                            d["hit_process"][~d["hit_primary"] & d["hit_common"]],
                            minlength=7,
                        )
                        / a.events
                    ).tolist(),
                )
            ),
            "secondary_process_hits_per_event": dict(
                zip(
                    PROC,
                    (
                        np.bincount(d["hit_process"][~d["hit_primary"]], minlength=7)
                        / a.events
                    ).tolist(),
                )
            ),
        }
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if a.coverage:
        cov = json.loads(a.coverage.read_text())
        rows = cov["surfaces"]
        groups = {
            "Full tracker": rows,
            "Pixel volumes 16–18": [
                r for r in rows if re.search(r"_vol(16|17|18)_", r["surface"])
            ],
        }
        fig, axes = plt.subplots(1, 2, figsize=(11, 5))
        for ax, (label, rs) in zip(axes, groups.items()):
            total = sum(r["bins"] for r in rs)
            matched = sum(r["silicon_match_bins"] for r in rs)
            ax.bar(
                ["All positive bins", "Match Si table"],
                [total, matched],
                color=["#2563a6", "#d55e00"],
            )
            ax.set_yscale("log")
            ax.set_ylabel("material-map bins")
            ax.set_title(label)
            ax.text(
                0.5,
                0.90,
                f"{matched:,} / {total:,} bins match ({100*matched/total:.4f}%)",
                ha="center",
                transform=ax.transAxes,
            )
        fig.suptitle("Current hadronic table coverage in the ODD map")
        save(
            fig,
            "material_coverage",
            "Ar/Z lookup at relative tolerance 0.001; counts are NOT weighted by track flux or interaction probability.",
        )
    fig = plt.figure(figsize=(11.7, 8.3))
    fig.suptitle("ODD Geant4 / Fatras validation", fontsize=17, y=0.94)
    lines = [
        f"{a.events} matched Pythia8 ttbar + Poisson PU200 events, 14 TeV; seed 42.",
        "ODD v6 tracker only (pixels + strips), uniform Bz = 2 T; pixel summaries below.",
        "K-short and Lambda are left undecayed by Pythia8; identical filtered inputs for all variants.",
        "Geant4 11.3.2 FTFP_BERT, configured time kill at 1000 ns; Fatras pMin = 100 MeV, pTMin = 50 MeV.",
        (
            "Fatras material-map correction enabled; Geant4 geometry unchanged. See run-metadata.json."
            if config["allow_material_map_change"]
            else "Fatras variant settings and source revisions are recorded in run-metadata.json."
        ),
        "",
        "Mean pixel hits per event (common hit-entry p / pT cuts):",
    ]
    for k, row in summary.items():
        lines.append(
            f"  {STYLE[k][1]}: primary {row['common_primary_pixel_hits_per_event']:,.0f}; secondary {row['common_secondary_pixel_hits_per_event']:,.0f}"
        )
    ratio = (
        summary["fatras"]["common_secondary_pixel_hits_per_event"]
        / summary["geant4"]["common_secondary_pixel_hits_per_event"]
    )
    lines += [
        "",
        f"Current Fatras retains {ratio:.1%} of Geant4 secondary pixel hits within the common momentum cuts.",
        "Creation-process plots identify the immediate parent process, not full shower ancestry.",
        f"Nuclear-created Fatras pixel hits/event: {summary['fatras']['secondary_process_hits_per_event']['nuclear']:,.1f}.",
        "",
        "Interpretation limits:",
        "• Simulation hits, before digitization or reconstruction; repeated sensor crossings retained.",
        "• Shared input and geometry source; Geant4 volume material versus Fatras mapped surfaces.",
        "• Momentum cuts on hits do not equalize earlier transport, shower history or production cuts.",
        "• Tracker-only reference excludes calorimeter backscatter; small sample, not a physics tune.",
        "• Ranges on distribution plots are display windows, not normalization selections.",
        "• Read README and run logs for propagation failures and Geant4 hit-buffer warnings.",
    ]
    fig.text(0.07, 0.84, "\n".join(lines), va="top", fontsize=11, linespacing=1.6)
    fig.savefig(a.output / "validation_summary.pdf")
    book.savefig(fig)
    plt.close(fig)
    book.close()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
