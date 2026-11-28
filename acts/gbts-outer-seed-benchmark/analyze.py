#!/usr/bin/env python3
"""Compare the GBTS seed fit variants of run_variants.py.

Run in a uv env: uv run --no-project --with uproot --with awkward --with numpy
"""

import argparse
import json
import pathlib

import awkward as ak
import numpy as np
import uproot

PIXEL = (16, 17, 18)
ID = ["vertex_primary", "vertex_secondary", "particle", "generation", "sub_particle"]


def key(parts):
    vp, vs, p, g, sub = parts
    return ((((vp * 1000 + vs) * 100000 + p) * 100 + g) * 1000) + sub


def sigma68(x):
    x = np.asarray(x)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return float("nan")
    lo, hi = np.percentile(x, [16, 84])
    return 0.5 * (hi - lo)


def tail(x, cut):
    x = np.asarray(x)
    x = x[np.isfinite(x)]
    return float(np.mean(np.abs(x) > cut)) if len(x) else float("nan")


def hist_sigma68(h):
    values, edges = h.to_numpy()
    c = np.cumsum(values)
    if c[-1] <= 0:
        return float("nan")
    c = c / c[-1]
    centers = 0.5 * (edges[1:] + edges[:-1])
    lo, hi = np.interp([0.16, 0.84], c, centers)
    return 0.5 * (hi - lo)


def innermost_pixel_layer(hitsFile):
    """(event, particle key) -> (volume, layer) of the innermost pixel sim hit."""
    h = uproot.open(hitsFile)["hits"].arrays(
        ["event_id", "volume_id", "layer_id", "tx", "ty"]
        + [f"barcode_{i}" for i in ID],
        library="np",
    )
    k = key([h[f"barcode_{i}"].astype(np.int64) for i in ID])
    pix = np.isin(h["volume_id"], PIXEL)
    r = np.hypot(h["tx"], h["ty"])
    order = np.lexsort((r[pix], k[pix], h["event_id"][pix]))
    ev = h["event_id"][pix][order]
    kk = k[pix][order]
    first = np.ones(len(ev), bool)
    first[1:] = (ev[1:] != ev[:-1]) | (kk[1:] != kk[:-1])
    vol = h["volume_id"][pix][order][first]
    lay = h["layer_id"][pix][order][first]
    return {
        (int(e), int(p)): (int(v), int(l))
        for e, p, v, l in zip(ev[first], kk[first], vol, lay)
    }


def inner_hits(summaryFile, statesFile, inner):
    s = uproot.open(summaryFile)["tracksummary"].arrays(
        ["event_nr", "trackClassification"]
        + [f"majorityParticleId_{i}" for i in ID]
    )
    t = uproot.open(statesFile)["trackstates"].arrays(
        ["event_nr", "track_nr", "stateType", "volume_id", "layer_id", "t_x",
         "t_y"] + [f"particle_ids_{i}" for i in ID]
    )
    # majority particle and class per (event, track)
    ev = ak.to_numpy(ak.flatten(ak.broadcast_arrays(s.event_nr, s.trackClassification)[0]))
    cls = ak.to_numpy(ak.flatten(s.trackClassification))
    tr = ak.to_numpy(ak.flatten(ak.local_index(s.trackClassification)))
    maj = key([ak.to_numpy(ak.flatten(s[f"majorityParticleId_{i}"])).astype(np.int64) for i in ID])
    summary = {(int(e), int(n)): (int(c), int(m)) for e, n, c, m in zip(ev, tr, cls, maj)}

    stats = dict(tracks=0, ok=0, wrong=0, missing=0, beyond=0, nopixel=0,
                 wrongPixelHits=0, pixelHits=0, restPure=0, restPureInnerWrong=0,
                 duplicates=0)
    # per state particle keys, flattened per state
    pk = key([ak.values_astype(t[f"particle_ids_{i}"], np.int64) for i in ID])
    meas = t.stateType == 0
    # the truth position of the hit, a seed has no calibrated one
    r = np.hypot(t.t_x, t.t_y)
    for j in range(len(t)):
        e = int(t.event_nr[j])
        n = int(t.track_nr[j])
        c, m = summary[(e, n)]
        # matched and duplicate tracks, not fakes
        if c not in (1, 2):
            continue
        stats["duplicates"] += int(c == 2)
        mj = ak.to_numpy(meas[j])
        vol = ak.to_numpy(t.volume_id[j])[mj]
        lay = ak.to_numpy(t.layer_id[j])[mj]
        rr = ak.to_numpy(r[j])[mj]
        keys = [list(x) for x, keep in zip(pk[j].tolist(), mj) if keep]
        stats["tracks"] += 1
        ispix = np.isin(vol, PIXEL)
        stats["pixelHits"] += int(ispix.sum())
        stats["wrongPixelHits"] += sum(
            1 for kk, p in zip(keys, ispix) if p and m not in kk
        )
        truthInner = inner.get((e, m))
        if truthInner is None:
            stats["nopixel"] += 1
            continue
        i = int(np.argmin(rr))
        rest = all(m in kk for k2, kk in enumerate(keys) if k2 != i)
        if rest:
            stats["restPure"] += 1
            stats["restPureInnerWrong"] += int(m not in keys[i])
        if m not in keys[i]:
            stats["wrong"] += 1
        elif (int(vol[i]), int(lay[i])) == truthInner:
            stats["ok"] += 1
        else:
            stats["missing"] += 1
    return stats


def seed_surface(vdir, name):
    t = uproot.open(vdir / f"{name}_estimatedparams.root")["estimatedparams"].arrays(
        ["truthMatched", "t_pt", "res_loc0", "res_loc1", "res_phi", "res_theta",
         "res_qop", "t_qop", "pull_loc0", "pull_loc1", "pull_phi", "pull_qop"],
        library="np",
    )
    t = {k: np.concatenate(v) if v.dtype == object else v for k, v in t.items()}
    out = {}
    for label, sel in [("pure", t["truthMatched"] == 1), ("impure", t["truthMatched"] != 1)]:
        d = {"n": int(sel.sum())}
        for v in ["loc0", "loc1", "phi", "theta"]:
            d[f"s68_{v}"] = sigma68(t[f"res_{v}"][sel])
        d["s68_qop_rel"] = sigma68(t["res_qop"][sel] / t["t_qop"][sel])
        for v in ["loc0", "loc1", "phi", "qop"]:
            d[f"tail5_{v}"] = tail(t[f"pull_{v}"][sel], 5)
        out[label] = d
    return out


def track_perigee(vdir, name, stage):
    s = uproot.open(vdir / f"tracksummary_{name}_{stage}.root")["tracksummary"].arrays(
        ["trackClassification", "hasFittedParams", "t_pT", "res_eLOC0_fit",
         "res_eLOC1_fit", "res_ePHI_fit", "res_eTHETA_fit", "res_eQOP_fit",
         "eQOP_fit", "pull_eLOC0_fit", "pull_eLOC1_fit", "pull_ePHI_fit",
         "pull_eTHETA_fit", "pull_eQOP_fit"],
    )
    sel = (s.trackClassification == 1) & s.hasFittedParams
    f = {k: ak.to_numpy(ak.flatten(s[k][sel])) for k in s.fields}
    d = {"n": len(f["t_pT"])}
    for v in ["eLOC0", "eLOC1", "ePHI", "eTHETA"]:
        d[f"s68_{v}"] = sigma68(f[f"res_{v}_fit"])
    qop_true = f["eQOP_fit"] - f["res_eQOP_fit"]
    d["s68_qop_rel"] = sigma68(f["res_eQOP_fit"] / qop_true)
    for v in ["eLOC0", "eLOC1", "ePHI", "eTHETA", "eQOP"]:
        d[f"pull68_{v}"] = sigma68(f[f"pull_{v}_fit"])
        d[f"tail5_{v}"] = tail(f[f"pull_{v}_fit"], 5)
    return d


def seed_perigee(vdir, name):
    g = uproot.open(vdir / f"performance_{name}_seedparams.root")
    return {
        f"s68_{v}": hist_sigma68(g[f"res_{v}"])
        for v in ["d0", "z0", "phi", "theta", "qopt_rel"]
    } | {
        f"pull68_{v}": hist_sigma68(g[f"pull_{v}"])
        for v in ["d0", "z0", "phi", "qopt"]
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dir", type=pathlib.Path)
    p.add_argument("--variants", nargs="+")
    a = p.parse_args()
    variants = a.variants or sorted(
        x.name for x in a.dir.iterdir() if x.is_dir()
    )
    inner = innermost_pixel_layer(a.dir / "hits.root") if (a.dir / "hits.root").exists() else {}
    result = {}
    for v in variants:
        vdir = a.dir / v
        r = {
            "seedSurface": seed_surface(vdir, v),
            "seedPerigee": seed_perigee(vdir, v),
            "track": track_perigee(vdir, v, "ckf"),
        }
        if (vdir / f"tracksummary_{v}_ambi.root").exists():
            r["ambiTrack"] = track_perigee(vdir, v, "ambi")
        if inner:
            r["innerHit"] = inner_hits(vdir / f"tracksummary_{v}_ckf.root",
                                       vdir / f"trackstates_{v}_ckf.root", inner)
            if (vdir / f"trackstates_{v}_ambi.root").exists():
                r["ambiInnerHit"] = inner_hits(
                    vdir / f"tracksummary_{v}_ambi.root",
                    vdir / f"trackstates_{v}_ambi.root", inner)
        result[v] = r
    if inner and (a.dir / "tracksummary_seeds.root").exists():
        result["seeds"] = inner_hits(a.dir / "tracksummary_seeds.root",
                                     a.dir / "trackstates_seeds.root", inner)
    print(json.dumps(result, indent=1))
    (a.dir / "analysis.json").write_text(json.dumps(result, indent=1))


main()
