#!/usr/bin/env python3
"""Efficiency, fakes, resolution and CPU of the CKF scattering tail modes.

A particle is a "tail" particle if Fatras recorded at least one scatter with a
projected angle above RATIO x Highland theta0 at rho > RHO_MIN (inside the
tracker). The flag comes from the scatter CSVs of the first run.
"""

import argparse
import glob
import json
import os
import pathlib

import numpy as np
import uproot
from scipy import stats
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.backends.backend_pdf import PdfPages

RATIO = 4.0
RHO_MIN = 30.0  # mm
# measured coordinates per volume in the ODD smearing config
NDF_BY_VOLUME = {16: 3, 17: 3, 18: 3, 23: 2, 24: 2, 25: 2, 28: 1, 29: 1, 30: 1}

# fixed categorical order, see the dataviz reference palette
CONFIGS = [
    ("base15", "baseline 15/25", "#2a78d6", "o"),
    ("base49", "baseline 49/100", "#eb6834", "s"),
    ("retry15", "retry 15/25", "#1baf7a", "^"),
    ("mix15", "mixture 15/25", "#eda100", "D"),
    ("branch15", "retry+branch 15/25", "#e87ba4", "v"),
    ("selonly15", "select only 15/25", "#008300", "P"),
    ("base25", "baseline 25/50", "#6250d6", "X"),
    ("base35", "baseline 35/70", "#e34948", "*"),
]
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"


def key(ev, vp, vs, p, g, sp):
    ev, vp, vs, p, g, sp = (np.asarray(x, dtype=np.uint64) for x in (ev, vp, vs, p, g, sp))
    return (
        (ev << np.uint64(51))
        | (vp << np.uint64(42))
        | (vs << np.uint64(30))
        | (p << np.uint64(14))
        | (g << np.uint64(8))
        | sp
    )


def load_tail(scatterDir):
    keys, ratios = [], []
    for f in glob.glob(os.path.join(scatterDir, "event*-scatters.csv")):
        ev = int(os.path.basename(f)[5:].split("-")[0])
        d = np.genfromtxt(f, delimiter=",", names=True)
        if d.size == 0:
            continue
        d = np.atleast_1d(d)
        rho = np.hypot(d["x"], d["y"])
        sel = rho > RHO_MIN
        d = d[sel]
        keys.append(key(np.full(len(d), ev), d["vp"], d["vs"], d["p"], d["g"], d["sp"]))
        ratios.append(d["ratio"])
    keys = np.concatenate(keys)
    ratios = np.concatenate(ratios)
    # max ratio per particle
    order = np.argsort(keys)
    keys, ratios = keys[order], ratios[order]
    uk, idx = np.unique(keys, return_index=True)
    maxr = np.maximum.reduceat(ratios, idx)
    return dict(zip(uk.tolist(), maxr.tolist()))


def flat(tree, names):
    arr = tree.arrays(names, library="np")
    return {n: np.concatenate(arr[n]) if arr[n].dtype == object else arr[n] for n in names}


def load_particles(path):
    t = uproot.open(path)["particles"]
    names = ["event_id", "vertex_primary", "vertex_secondary", "particle", "generation",
             "sub_particle", "pt", "eta", "q", "p"]
    arr = t.arrays(names, library="np")
    ev = np.concatenate([np.full(len(x), e) for e, x in zip(arr["event_id"], arr["pt"])])
    d = {n: np.concatenate(arr[n]) for n in names[1:]}
    d["key"] = key(ev, d["vertex_primary"], d["vertex_secondary"], d["particle"],
                   d["generation"], d["sub_particle"])
    return d


def load_run(runDir, stage):
    f = uproot.open(os.path.join(runDir, f"performance_finding_{stage}.root"))
    m = f["matchingdetails"].arrays(library="np")
    mk = key(m["event_nr"], m["particle_id_vertex_primary"], m["particle_id_vertex_secondary"],
             m["particle_id_particle"], m["particle_id_generation"], m["particle_id_sub_particle"])
    t = uproot.open(os.path.join(runDir, f"tracksummary_{stage}.root"))["tracksummary"]
    names = ["nMeasurements", "nOutliers", "nHoles", "trackClassification", "hasFittedParams",
             "majorityParticleId_vertex_primary", "majorityParticleId_vertex_secondary",
             "majorityParticleId_particle", "majorityParticleId_generation",
             "majorityParticleId_sub_particle", "t_pT", "t_eta", "t_p", "t_charge",
             "eQOP_fit", "eTHETA_fit",
             "res_eLOC0_fit", "res_eLOC1_fit", "res_ePHI_fit", "res_eTHETA_fit", "res_eQOP_fit",
             "pull_eLOC0_fit", "pull_eLOC1_fit", "pull_ePHI_fit", "pull_eTHETA_fit",
             "pull_eQOP_fit", "chi2Sum", "NDF"]
    arr = t.arrays(names + ["event_nr"], library="np")
    ev = np.concatenate([np.full(len(x), e) for e, x in zip(arr["event_nr"], arr["t_pT"])])
    tr = {n: np.concatenate(arr[n]) for n in names}
    tr["key"] = key(ev, tr["majorityParticleId_vertex_primary"],
                    tr["majorityParticleId_vertex_secondary"], tr["majorityParticleId_particle"],
                    tr["majorityParticleId_generation"], tr["majorityParticleId_sub_particle"])
    nev = len(arr["event_nr"])
    # per-state chi2, flattened, with the index of the owning track
    st = t.arrays(["measurementChi2", "measurementVolume"], library="np")
    chi2s, ndfs, owner, fromInner = [], [], [], []
    itrack = 0
    for evChi2, evVol in zip(st["measurementChi2"], st["measurementVolume"]):
        for c, v in zip(evChi2, evVol):
            c = np.asarray(c, dtype=float)
            chi2s.append(c)
            ndfs.append(np.vectorize(NDF_BY_VOLUME.get)(np.asarray(v)) if len(v) else np.zeros(0))
            owner.append(np.full(len(c), itrack))
            # states are stored outermost first
            fromInner.append(np.arange(len(c))[::-1])
            itrack += 1
    tr["state_chi2"] = np.concatenate(chi2s)
    tr["state_ndf"] = np.concatenate(ndfs).astype(float)
    tr["state_owner"] = np.concatenate(owner)
    tr["state_from_inner"] = np.concatenate(fromInner)
    return {"matchKey": mk, "matched": m["matched"].astype(bool), "tracks": tr, "nev": nev}


def binom(k, n):
    e = k / n if n else np.nan
    return e, (np.sqrt(e * (1 - e) / n) if n else np.nan)


def q68(x):
    x = np.abs(x[np.isfinite(x)])
    return np.quantile(x, 0.6827) if len(x) else np.nan


def load_timing(timingDir):
    out = {}
    for name, *_ in CONFIGS:
        vals = []
        for f in sorted(glob.glob(os.path.join(timingDir, f"{name}_r*", "timing.csv"))):
            for line in open(f):
                if line.startswith("Algorithm:TrackFindingAlgorithm"):
                    vals.append(float(line.split(",")[2]))
        if vals:
            out[name] = vals
    return out


def ptaxis(ax):
    ax.set_xscale("log")
    ticks = [1, 2, 5, 10, 20, 50, 100]
    ax.set_xticks(ticks, [str(t) for t in ticks])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())


def style(ax):
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(INK2)
    ax.tick_params(colors=INK2)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(INK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", type=pathlib.Path)
    ap.add_argument("--timing", type=pathlib.Path)
    ap.add_argument("--stage", default="ambi")
    ap.add_argument("--pdf", type=pathlib.Path, required=True)
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--model", type=pathlib.Path, help="tail model npz from fitmix.py")
    ap.add_argument("--export", type=pathlib.Path, help="all curves as JSON for the report")
    a = ap.parse_args()

    tail = load_tail(a.runs / "base15" / "scatters")
    parts = load_particles(a.runs / "truth" / "particles_selected.root")
    pmaxr = np.array([tail.get(k, 0.0) for k in parts["key"].tolist()])
    primary = (parts["vertex_secondary"] == 0) & (parts["generation"] == 0)
    isTail = pmaxr > RATIO
    pIndex = {k: i for i, k in enumerate(parts["key"].tolist())}

    runs = {}
    for name, *_ in CONFIGS:
        d = a.runs / name
        if (d / f"tracksummary_{a.stage}.root").exists():
            runs[name] = load_run(d, a.stage)
    timing = load_timing(a.timing) if a.timing else {}

    summary = {}
    ptBins = np.array([1, 1.5, 2, 3, 5, 10, 20, 100])
    etaBins = np.linspace(-3, 3, 13)
    curves = {}
    for name, r in runs.items():
        idx = np.array([pIndex.get(k, -1) for k in r["matchKey"].tolist()])
        ok = idx >= 0
        mi, mm = idx[ok], r["matched"][ok]
        prim = primary[mi]
        t, pt, eta = isTail[mi], parts["pt"][mi], parts["eta"][mi]
        s = {}
        for lab, sel in (("all", prim), ("tail", prim & t), ("core", prim & ~t)):
            s[f"eff_{lab}"], s[f"eff_{lab}_err"] = binom(mm[sel].sum(), sel.sum())
            s[f"n_{lab}"] = int(sel.sum())
        cv = {}
        for lab, sel in (("tail", prim & t), ("core", prim & ~t)):
            for var, x, bins in (("pt", pt, ptBins), ("eta", eta, etaBins)):
                b = np.digitize(x[sel], bins) - 1
                e, err = [], []
                for i in range(len(bins) - 1):
                    v, u = binom(mm[sel][b == i].sum(), (b == i).sum())
                    e.append(v)
                    err.append(u)
                cv[f"{lab}_{var}"] = (np.array(e), np.array(err))

        tr = r["tracks"]
        cls = tr["trackClassification"]
        sel = (tr["t_pT"] > 0) | (cls == 3)
        ntr = len(cls)
        s["tracks_per_event"] = ntr / r["nev"]
        s["fake_rate"], s["fake_rate_err"] = binom((cls == 3).sum(), ntr)
        s["dup_rate"], _ = binom((cls == 2).sum(), ntr)
        # fake rate vs reco pT
        recoPt = np.abs(1 / tr["eQOP_fit"]) * np.sin(tr["eTHETA_fit"])
        recoEta = -np.log(np.tan(tr["eTHETA_fit"] / 2))
        for var, x, bins in (("pt", recoPt, ptBins), ("eta", recoEta, etaBins)):
            b = np.digitize(x, bins) - 1
            e, err = [], []
            for i in range(len(bins) - 1):
                v, u = binom((cls[b == i] == 3).sum(), (b == i).sum())
                e.append(v)
                err.append(u)
            cv[f"fake_{var}"] = (np.array(e), np.array(err))

        # resolution of matched tracks, by truth flag of the majority particle
        m1 = (cls == 1) & tr["hasFittedParams"].astype(bool)
        tmaxr = np.array([tail.get(k, 0.0) for k in tr["key"].tolist()])
        tt = tmaxr > RATIO
        # the first measurements fix the 6 track parameters (time included) from
        # the wide seed covariance and add almost no chi2
        trackP = stats.chi2.sf(tr["chi2Sum"], np.maximum(tr["NDF"] - 6, 1))
        # drop the three innermost (seed) measurements, which the wide seed
        # covariance absorbs with a chi2 near zero
        notSeed = tr["state_from_inner"] >= 3
        stateP = stats.chi2.sf(tr["state_chi2"], tr["state_ndf"])
        stateP[~notSeed] = np.nan
        stTail = tt[tr["state_owner"]]
        stMatched = m1[tr["state_owner"]]
        pv = {
            "track_all": trackP,
            "track_tail": trackP[m1 & tt],
            "track_core": trackP[m1 & ~tt],
            "state_all": stateP,
            "state_tail": stateP[stMatched & stTail],
            "state_core": stateP[stMatched & ~stTail],
        }
        s["frac_track_p_lt_1e-3"] = float((trackP < 1e-3).mean())
        s["frac_state_p_lt_1e-3"] = float((stateP[notSeed] < 1e-3).mean())
        tqop = tr["t_charge"] / tr["t_p"]
        relQop = tr["res_eQOP_fit"] / np.abs(tqop)
        res = {}
        for lab, ss in (("tail", m1 & tt), ("core", m1 & ~tt)):
            res[lab] = {
                "n": int(ss.sum()),
                "d0_q68_um": 1e3 * q68(tr["res_eLOC0_fit"][ss]),
                "z0_q68_um": 1e3 * q68(tr["res_eLOC1_fit"][ss]),
                "phi_q68_mrad": 1e3 * q68(tr["res_ePHI_fit"][ss]),
                "theta_q68_mrad": 1e3 * q68(tr["res_eTHETA_fit"][ss]),
                "qop_rel_q68": q68(relQop[ss]),
            }
            for par in ("eLOC0", "eLOC1", "ePHI", "eTHETA", "eQOP"):
                pull = tr[f"pull_{par}_fit"][ss]
                pull = pull[np.isfinite(pull)]
                res[lab][f"pull_{par}_q68"] = q68(pull)
                res[lab][f"pull_{par}_gt5"] = float((np.abs(pull) > 5).mean()) if len(pull) else np.nan
            res[lab]["_d0"] = tr["res_eLOC0_fit"][ss]
            res[lab]["_qop"] = relQop[ss]
            res[lab]["_pull_qop"] = tr["pull_eQOP_fit"][ss]
            res[lab]["_pull_d0"] = tr["pull_eLOC0_fit"][ss]
            res[lab]["_nmeas"] = tr["nMeasurements"][ss]
        s["res"] = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in res.items()}
        s["nmeas_tail"] = float(np.mean(res["tail"]["_nmeas"]))
        s["nmeas_core"] = float(np.mean(res["core"]["_nmeas"]))
        if name in timing:
            s["ckf_s_per_event"] = float(np.mean(timing[name]))
            s["ckf_s_per_event_spread"] = float(np.std(timing[name]))
            s["ckf_s_runs"] = timing[name]
        log = a.runs / f"{name}.log"
        if log.exists():
            for line in open(log):
                if "scattering tail:" in line:
                    s["tail_states_per_event"] = int(line.rsplit(":", 1)[1]) / r["nev"]
        summary[name] = s
        curves[name] = (cv, res, pv)

    if a.json:
        a.json.write_text(json.dumps(summary, indent=1, default=float))

    if a.export:
        def hist(v, bins, density=True):
            v = v[np.isfinite(v)]
            h, _ = np.histogram(v, bins=bins)
            if density:
                return (h / max(len(v), 1) / np.diff(bins)).tolist()
            return (h / max(len(v), 1)).tolist()

        def rnd(x, n=5):
            return [None if not np.isfinite(y) else round(float(y), n) for y in np.asarray(x, dtype=float)]

        linBins = np.linspace(0, 1, 41)
        logBins = np.logspace(-12, 0, 49)
        d0Bins = np.linspace(-500, 500, 101)
        pullBins = np.linspace(-10, 10, 101)
        exp = {
            "meta": {
                "events": runs[next(iter(runs))]["nev"],
                "ratio": RATIO,
                "rhoMin": RHO_MIN,
                "tailFraction": float(isTail[primary].mean()),
                "nPrimaries": int(primary.sum()),
            },
            "configs": [{"id": n, "label": l, "color": c} for n, l, c, _ in CONFIGS if n in summary],
            "summary": summary,
            "ptBins": ptBins.tolist(),
            "etaBins": etaBins.tolist(),
            "linBins": linBins.tolist(),
            "logBins": np.log10(logBins).tolist(),
            "d0Bins": d0Bins.tolist(),
            "pullBins": pullBins.tolist(),
            "timing": timing,
            "curves": {},
        }
        for n in summary:
            cv, res, pv = curves[n]
            c = {k: {"e": rnd(v[0]), "err": rnd(v[1])} for k, v in cv.items()}
            for k in ("track_all", "track_tail", "track_core", "state_all", "state_tail", "state_core"):
                c[f"p_{k}"] = rnd(hist(pv[k], linBins))
            for k in ("track_all", "state_all"):
                v = np.clip(pv[k][np.isfinite(pv[k])], 1e-12, 1)
                c[f"plog_{k}"] = rnd(hist(v, logBins, density=False), 7)
            rt = res["tail"]
            c["d0_tail"] = rnd(hist(np.clip(1e3 * rt["_d0"], -499.9, 499.9), d0Bins), 7)
            c["pullqop_tail"] = rnd(hist(np.clip(rt["_pull_qop"], -9.99, 9.99), pullBins), 7)
            c["pulld0_tail"] = rnd(hist(np.clip(rt["_pull_d0"], -9.99, 9.99), pullBins), 7)
            exp["curves"][n] = c
        if a.model and a.model.exists():
            mdl = np.load(a.model)
            xs = 0.5 * (mdl["bins"][1:] + mdl["bins"][:-1])
            h, _ = np.histogram(mdl["x"], bins=mdl["bins"], density=True)
            exp["model"] = {"x": rnd(xs, 3), "sampled": rnd(h, 8), "fit": rnd(mdl["fit"], 8),
                            "hl": rnd(mdl["hl"], 8), "ts": mdl["ts"].tolist(),
                            "eps": rnd(mdl["eps"]), "k": rnd(mdl["k"], 3)}
        a.export.write_text(json.dumps(exp, default=float))

    labels = {n: (l, c, mk) for n, l, c, mk in CONFIGS}
    order = [n for n, *_ in CONFIGS if n in summary]
    with PdfPages(a.pdf) as pdf:
        # page 1: table
        fig = plt.figure(figsize=(11.7, 8.3))
        fig.text(0.04, 0.95, "CKF scattering tail prototype: ODD ttbar <mu>=200, Fatras general mixture",
                 fontsize=14, color=INK, weight="bold")
        nev = runs[order[0]]["nev"]
        fig.text(0.04, 0.915,
                 f"{nev} events, output after greedy ambiguity resolution. Primary particles, pT > 1 GeV, |eta| < 3, >= 9 measurements. "
                 f"Tail particle: >= 1 scatter > {RATIO:g} x Highland at rho > {RHO_MIN:g} mm "
                 f"({isTail[primary].mean():.1%} of the selected primaries).",
                 fontsize=8.5, color=INK2, wrap=True)
        metricRows = [
            ("efficiency, all primaries [%]", lambda s: f"{100*s['eff_all']:.2f}"),
            ("efficiency, tail primaries [%]", lambda s: f"{100*s['eff_tail']:.2f} ± {100*s['eff_tail_err']:.2f}"),
            ("efficiency, no-tail primaries [%]", lambda s: f"{100*s['eff_core']:.2f} ± {100*s['eff_core_err']:.2f}"),
            ("fake rate [%]", lambda s: f"{100*s['fake_rate']:.3f} ± {100*s['fake_rate_err']:.3f}"),
            ("duplicate rate [%]", lambda s: f"{100*s['dup_rate']:.3f}"),
            ("tracks / event", lambda s: f"{s['tracks_per_event']:.1f}"),
            ("tail-accepted states / event (all branches)", lambda s: f"{s.get('tail_states_per_event', 0):.0f}"),
            ("measurements / matched tail track", lambda s: f"{s['nmeas_tail']:.2f}"),
            ("d0 residual q68, tail [µm]", lambda s: f"{s['res']['tail']['d0_q68_um']:.1f}"),
            ("d0 residual q68, no tail [µm]", lambda s: f"{s['res']['core']['d0_q68_um']:.1f}"),
            ("q/p rel. residual q68, tail [%]", lambda s: f"{100*s['res']['tail']['qop_rel_q68']:.2f}"),
            ("q/p rel. residual q68, no tail [%]", lambda s: f"{100*s['res']['core']['qop_rel_q68']:.2f}"),
            ("q/p pull q68, tail", lambda s: f"{s['res']['tail']['pull_eQOP_q68']:.3f}"),
            ("q/p pull q68, no tail", lambda s: f"{s['res']['core']['pull_eQOP_q68']:.3f}"),
            ("|q/p pull| > 5, tail [%]", lambda s: f"{100*s['res']['tail']['pull_eQOP_gt5']:.2f}"),
            ("|d0 pull| > 5, tail [%]", lambda s: f"{100*s['res']['tail']['pull_eLOC0_gt5']:.2f}"),
            ("tracks with p < 1e-3 [%]", lambda s: f"{100*s['frac_track_p_lt_1e-3']:.2f}"),
            ("non-seed states with selection p < 1e-3 [%]", lambda s: f"{100*s['frac_state_p_lt_1e-3']:.2f}"),
            ("CKF time, 1 thread [s / event]", lambda s: (f"{s['ckf_s_per_event']:.3f} ± {s['ckf_s_per_event_spread']:.3f}" if "ckf_s_per_event" in s else "–")),
        ]
        cols = ["metric"] + [labels[n][0] for n in order]
        rows = [[m] + [f(summary[n]) for n in order] for m, f in metricRows]
        ax = fig.add_axes([0.02, 0.12, 0.96, 0.76])
        ax.axis("off")
        tb = ax.table(cellText=rows, colLabels=cols, loc="upper center", cellLoc="center",
                      colWidths=[0.28] + [0.12] * len(order))
        tb.auto_set_font_size(False)
        tb.set_fontsize(8)
        tb.scale(1, 1.45)
        for (i, j), c in tb.get_celld().items():
            c.set_edgecolor(GRID)
            if j == 0:
                c.get_text().set_ha("left")
                c._loc = "left"
            if i == 0:
                c.set_text_props(weight="bold", color=INK)
        for j, n in enumerate(order, start=1):
            tb[0, j].get_text().set_color(labels[n][1])
        fig.text(0.04, 0.05,
                 "eff: fraction of primaries with a matched track (TrackTruthMatcher). Errors are binomial. "
                 "Resolution: matched tracks only, q68 = 68% quantile of |residual|.\n"
                 "tail states/ev: track states accepted only through the tail (retry success, or mixture posterior tail weight > 0.5), "
                 "over all CKF branches.",
                 fontsize=8, color=INK2)
        pdf.savefig(fig)
        plt.close(fig)

        # page 2: efficiency curves
        fig, axs = plt.subplots(2, 2, figsize=(11.7, 8.3))
        for (row, lab) in enumerate(("tail", "core")):
            for (col, var, bins, xl) in ((0, "pt", ptBins, "truth pT [GeV]"), (1, "eta", etaBins, "truth eta")):
                ax = axs[row, col]
                xc = 0.5 * (bins[1:] + bins[:-1])
                for k, n in enumerate(order):
                    e, err = curves[n][0][f"{lab}_{var}"]
                    off = (k - len(order) / 2) * (0.012 if var == "pt" else 0.04)
                    x = xc * (1 + off) if var == "pt" else xc + off
                    ax.errorbar(x, e, yerr=err, fmt=labels[n][2], ms=4, lw=1.5, color=labels[n][1],
                                label=labels[n][0], capsize=0)
                if var == "pt":
                    ptaxis(ax)
                ax.set_xlabel(xl)
                ax.set_ylabel("efficiency")
                ax.set_title(f"{'tail' if lab == 'tail' else 'no tail'} particles", fontsize=10, loc="left")
                style(ax)
        axs[0, 0].legend(fontsize=7.5, frameon=False, ncol=2)
        fig.suptitle("Track efficiency, split by the truth tail flag", color=INK)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # page 3: fake rate
        fig, axs = plt.subplots(1, 2, figsize=(11.7, 4.6))
        for (col, var, bins, xl) in ((0, "pt", ptBins, "reco pT [GeV]"), (1, "eta", etaBins, "reco eta")):
            ax = axs[col]
            xc = 0.5 * (bins[1:] + bins[:-1])
            for k, n in enumerate(order):
                e, err = curves[n][0][f"fake_{var}"]
                off = (k - len(order) / 2) * (0.012 if var == "pt" else 0.04)
                x = xc * (1 + off) if var == "pt" else xc + off
                ax.errorbar(x, 100 * e, yerr=100 * err, fmt=labels[n][2], ms=4, lw=1.5,
                            color=labels[n][1], label=labels[n][0])
            if var == "pt":
                ptaxis(ax)
            ax.set_xlabel(xl)
            ax.set_ylabel("fake rate [%]")
            style(ax)
        axs[0].legend(fontsize=7.5, frameon=False, ncol=2)
        fig.suptitle("Fake rate of the output tracks (classification Fake)", color=INK)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # page 4: resolution and pull summaries
        metrics = [("d0_q68_um", "d0 residual q68 [µm]"), ("z0_q68_um", "z0 residual q68 [µm]"),
                   ("phi_q68_mrad", "phi residual q68 [mrad]"), ("qop_rel_q68", "q/p rel. residual q68"),
                   ("pull_eQOP_q68", "q/p pull q68"), ("pull_eLOC0_q68", "d0 pull q68"),
                   ("pull_eQOP_gt5", "fraction |q/p pull| > 5"), ("pull_eLOC0_gt5", "fraction |d0 pull| > 5")]
        fig, axs = plt.subplots(2, 4, figsize=(11.7, 6.4))
        for ax, (mkey, title) in zip(axs.flat, metrics):
            for j, lab in enumerate(("tail", "core")):
                for k, n in enumerate(order):
                    v = summary[n]["res"][lab][mkey]
                    ax.plot(j + (k - len(order) / 2 + 0.5) * 0.1, v, labels[n][2], ms=6,
                            color=labels[n][1], label=labels[n][0] if j == 0 else None)
            ax.set_xticks([0, 1], ["tail", "no tail"])
            ax.set_xlim(-0.5, 1.5)
            ax.set_title(title, fontsize=9, loc="left")
            style(ax)
        axs[0, 0].legend(fontsize=6.5, frameon=False)
        fig.suptitle("Perigee resolution and pulls of matched tracks", color=INK)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # page 5: distributions for tail tracks
        fig, axs = plt.subplots(1, 3, figsize=(11.7, 4.4))
        for n in order:
            r = curves[n][1]["tail"]
            kw = dict(histtype="step", lw=1.5, color=labels[n][1], label=labels[n][0], density=True)
            axs[0].hist(np.clip(1e3 * r["_d0"], -500, 500), bins=100, **kw)
            axs[1].hist(np.clip(r["_pull_qop"], -10, 10), bins=100, **kw)
            axs[2].hist(np.clip(r["_pull_d0"], -10, 10), bins=100, **kw)
        for ax, xl in zip(axs, ("d0 residual [µm]", "q/p pull", "d0 pull")):
            ax.set_yscale("log")
            ax.set_xlabel(xl)
            style(ax)
        axs[0].legend(fontsize=7, frameon=False)
        fig.suptitle("Matched tail tracks: residual and pull distributions (overflow in the edge bins)", color=INK)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # page: p-value distributions
        fig, axs = plt.subplots(2, 3, figsize=(11.7, 7.4))
        bins = np.linspace(0, 1, 41)
        panels = [("track_all", "track p-value, all tracks"),
                  ("track_tail", "track p-value, matched tail tracks"),
                  ("track_core", "track p-value, matched no-tail tracks"),
                  ("state_all", "state p-value, all tracks"),
                  ("state_tail", "state p-value, matched tail tracks"),
                  ("state_core", "state p-value, matched no-tail tracks")]
        for ax, (pk, title) in zip(axs.flat, panels):
            for n in order:
                v = curves[n][2][pk]
                v = v[np.isfinite(v)]
                ax.hist(v, bins=bins, histtype="step", lw=1.5, color=labels[n][1],
                        label=labels[n][0], weights=np.full(len(v), len(bins) - 1) / max(len(v), 1))
            ax.axhline(1, color=INK2, lw=0.8, ls="--")
            ax.set_yscale("log")
            ax.set_xlabel("p-value")
            ax.set_ylabel("density")
            ax.set_title(title, fontsize=9, loc="left")
            style(ax)
        axs[0, 0].legend(fontsize=7, frameon=False)
        fig.suptitle("Track p-value: Kalman chi2Sum with NDF - 6 (fitted parameters incl. time).  State p-value: the predicted chi2 the selection used "
                     "(mixture: chi2_mix), ndf = measurement dimension,\nwithout the 3 innermost (seed) measurements. "
                     "Dashed: uniform", color=INK, fontsize=9.5)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # page: low p-value region, log scale
        fig, axs = plt.subplots(1, 2, figsize=(11.7, 4.4))
        lbins = np.logspace(-12, 0, 49)
        for ax, (pk, title) in zip(axs, (("track_all", "track p-value, all tracks"),
                                         ("state_all", "state p-value, all tracks"))):
            for n in order:
                v = curves[n][2][pk]
                v = np.clip(v[np.isfinite(v)], 1e-12, 1)
                ax.hist(v, bins=lbins, histtype="step", lw=1.5, color=labels[n][1],
                        label=labels[n][0], weights=np.full(len(v), 1 / max(len(v), 1)))
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("p-value (underflow at 1e-12)")
            ax.set_ylabel("fraction per bin")
            ax.set_title(title, fontsize=9, loc="left")
            style(ax)
        axs[0].legend(fontsize=7, frameon=False)
        fig.suptitle("Low p-value region", color=INK, fontsize=10)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # page 6: CPU
        if timing:
            fig, ax = plt.subplots(figsize=(8.3, 4.6))
            names = [n for n in order if n in timing]
            for i, n in enumerate(names):
                vals = np.array(timing[n])
                ax.bar(i, vals.mean(), color=labels[n][1], width=0.6)
                ax.plot(np.full(len(vals), i), vals, "o", ms=4, color=INK2)
                ax.text(i, vals.mean() * 1.01, f"{vals.mean():.2f}", ha="center", va="bottom",
                        fontsize=8, color=INK)
            ax.set_xticks(range(len(names)), [labels[n][0] for n in names], rotation=20, fontsize=8)
            ax.set_ylabel("TrackFindingAlgorithm [s / event]")
            ax.set_title("CKF time, single thread, dots are the individual runs", fontsize=10, loc="left")
            style(ax)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        # page 7: tail model
        if a.model and a.model.exists():
            mdl = np.load(a.model)
            fig, axs = plt.subplots(1, 2, figsize=(11.7, 4.4))
            ax = axs[0]
            ax.hist(mdl["x"], bins=mdl["bins"], density=True, histtype="step", lw=1.5,
                    color="#2a78d6", label="Fatras general mixture (sampled)")
            xs = 0.5 * (mdl["bins"][1:] + mdl["bins"][:-1])
            ax.plot(xs, mdl["fit"], color="#eb6834", lw=1.5, label="two-Gaussian fit (reco tail model)")
            ax.plot(xs, mdl["hl"], color=INK2, lw=1, ls="--", label="Highland Gaussian (KF core)")
            ax.set_yscale("log")
            ax.set_ylim(1e-6, None)
            ax.set_xlabel("projected angle / Highland theta0")
            ax.set_title(f"t = {float(mdl['t']):.0%} X0, Si", fontsize=10, loc="left")
            ax.legend(fontsize=7.5, frameon=False)
            style(ax)
            ax = axs[1]
            ax.plot(mdl["ts"], mdl["eps"], "o-", color="#2a78d6", label="tail weight eps")
            ax.set_xscale("log")
            ax.set_xticks(mdl["ts"], [f"{t:.1%}" for t in mdl["ts"]])
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_xlabel("x / X0")
            ax.set_ylabel("tail weight")
            ax.set_title("Reco tail model: tail weight, and tail width k in units of Highland", fontsize=10, loc="left")
            for t_, e_, k_ in zip(mdl["ts"], mdl["eps"], mdl["k"]):
                ax.annotate(f"k={k_:.1f}", (t_, e_), textcoords="offset points", xytext=(0, 6),
                            ha="center", fontsize=7, color=INK2)
            style(ax)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    print(json.dumps({n: {k: v for k, v in s.items() if k != "res"} for n, s in summary.items()}, indent=1, default=float))


if __name__ == "__main__":
    main()
