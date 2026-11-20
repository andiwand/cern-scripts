#!/usr/bin/env python3
"""Chart data (charts.js format) and a text summary from IDPVM outputs of several variants; differences vs the first.
usage: charts.py <ana dir> out.json <base variant> <variant>...  (needs the asetup env for ROOT)
Reads <ana dir>/<v>/idpvm_{hs,all}.root and, if present, <ana dir>/lrtfakes.json (lrtfakes.py).
Everything vs |eta| is folded over +-eta."""
import sys, json, math, os, ROOT
D, OUT = sys.argv[1:3]; VS = sys.argv[3:]; V0 = VS[0]
LAB = {"b0": "main", "bP1": "branch strip L0, pixel seeds", "bP2": "branch strip L0-1, pixel seeds",
       "bA2": "branch strip L0-1, all seeds", "bP2e": "branch L0-1 pixel seeds + edge 1 mm", "e1": "edge 1 mm only (MR 92667)",
       "sP": "branch all strip layers, pixel seeds", "eP0": "branch strip endcap disk 0, pixel seeds",
       "bPe0": "branch strip L0 + endcap disk 0, pixel seeds"}
COL = dict(zip(VS, os.environ.get("COLS", "--p1 --p2 --p3 --p4 --p6 --p5 --grey").split()))
SHORT = {"b0": "main", "bP1": "L0 pix", "bP2": "L0-1 pix", "bA2": "L0-1 all", "bP2e": "L0-1 pix + edge", "e1": "edge", "sP": "all strip pix", "eP0": "EC0 pix", "bPe0": "L0+EC0 pix"}
F = {v: {s: ROOT.TFile.Open(f"{D}/{v}/idpvm_{s}.root") for s in ("hs", "all")} for v in VS}
G = lambda v, s, p: F[v][s].Get("SquirrelPlots/Tracks/" + p)
ETA = [0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0]
ETAF = [round(0.25 * i, 2) for i in range(17)]
PT = [1.0, 1.34, 1.8, 2.41, 3.24, 5.03, 10.5, 25.36, 1000]
PTF = [0.5, 1, 1.5, 2, 3, 5, 10, 30]
XL = {"eta": "|η|", "pt": "pT [GeV]"}

def lab(E): return [f"{x:g}" if x < 1000 else "∞" for x in E]
def fold(h, E, absx=True):
    """bin contents of a TH1 summed into new edges (by bin centre); returns list of sums"""
    s = [0.0] * (len(E) - 1); a = h.GetXaxis()
    for i in range(1, a.GetNbins() + 1):
        x = a.GetBinCenter(i); x = abs(x) if absx else x
        for k in range(len(E) - 1):
            if E[k] <= x < E[k + 1]: s[k] += h.GetBinContent(i); break
    return s
def eff(te, E, absx=True, minn=20):
    p, t = fold(te.GetPassedHistogram(), E, absx), fold(te.GetTotalHistogram(), E, absx)
    v, e = [], []
    for a, b in zip(p, t):
        if b < minn: v.append(None); e.append(None); continue
        r = a / b; v.append(round(100 * r, 4)); e.append(round(100 * math.sqrt(max(r * (1 - r), 1 / b) / b), 4))
    return v, e, t, p
def prof(pr, E):
    """TProfile folded in |eta|: entry-weighted mean and its error"""
    a = pr.GetXaxis(); n = [0.0] * (len(E) - 1); s = [0.0] * (len(E) - 1); s2 = [0.0] * (len(E) - 1)
    for i in range(1, a.GetNbins() + 1):
        x = abs(a.GetBinCenter(i)); w = pr.GetBinEntries(i)
        if w <= 0: continue
        m = pr.GetBinContent(i); sd = pr.GetBinError(i) * math.sqrt(w)   # spread option: error = sd/sqrt(n)
        for k in range(len(E) - 1):
            if E[k] <= x < E[k + 1]: n[k] += w; s[k] += w * m; s2[k] += w * (sd * sd + m * m); break
    v, e = [], []
    for k in range(len(E) - 1):
        if n[k] < 20: v.append(None); e.append(None); continue
        m = s[k] / n[k]; var = max(s2[k] / n[k] - m * m, 0); v.append(round(m, 4)); e.append(round(math.sqrt(var / n[k]), 4))
    return v, e
def itrms(h):
    """iterative RMS: mean +- 3 RMS window until stable; returns (rms, err, mean, mean err, n)"""
    if h.GetEntries() < 50: return None
    a = h.GetXaxis(); a.SetRange(0, 0); m, r = h.GetMean(), h.GetRMS()
    for _ in range(20):
        lo, hi = a.FindBin(m - 3 * r), a.FindBin(m + 3 * r); a.SetRange(lo, hi)
        m2, r2 = h.GetMean(), h.GetRMS()
        if abs(r2 - r) < 1e-3 * r: r, m = r2, m2; break
        r, m = r2, m2
    n = h.Integral(a.GetFirst(), a.GetLast()); a.SetRange(0, 0)
    return r, r / math.sqrt(2 * n), m, r / math.sqrt(n), n
def width2d(h2, E, scale=1.0, mean=False):
    v, e = [], []
    for k in range(len(E) - 1):
        bins = [i for i in range(1, h2.GetNbinsX() + 1) if E[k] <= abs(h2.GetXaxis().GetBinCenter(i)) < E[k + 1]]
        p = None
        for i in bins:
            q = h2.ProjectionY(f"_p{id(h2)}_{k}_{i}", i, i)
            if p is None: p = q.Clone(f"_s{id(h2)}_{k}")
            else: p.Add(q)
        x = itrms(p) if p else None
        if x is None: v.append(None); e.append(None); continue
        if mean: v.append(round(x[2] * scale, 5)); e.append(round(x[3] * scale, 5))
        else: v.append(round(x[0] * scale, 5)); e.append(round(x[1] * scale, 5))
    return v, e
def line(title, x, E, series, unit, ymin=None, ymax=None, col="L", nlabel=None, n=None):
    return dict(kind="line", title=title, x=x, edges=lab(E), xlabel=XL[x], series=series, ylabel=unit, unit=unit,
                ymin=ymin, ymax=ymax, col=col, nlabel=nlabel, n=n)
def diff(a, b):
    """b - a in % points, errors added in quadrature (conservative: the samples share events)"""
    v = [None if x is None or y is None else round(y - x, 4) for x, y in zip(a["v"], b["v"])]
    e = [None if x is None or y is None else round(math.hypot(x, y), 4) for x, y in zip(a["e"], b["e"])]
    return v, e

figs, summ = {}, {}
# efficiency and fakes
for x, E, hn in (("eta", ETA, "efficiency_vs_eta"), ("pt", PT, "efficiency_vs_pt_log")):
    panels = []
    for s, t in (("hs", "hard-scatter"), ("all", "hard-scatter + pile-up")):
        ser = {}
        for v in VS:
            val, err, tot, pas = eff(G(v, s, "Efficiency/" + hn), E, x == "eta")
            ser[v] = dict(label=LAB.get(v, v), color=COL[v], v=val, e=err, n=[int(z) for z in tot])
            summ[f"eff {s} {v}"] = (sum(pas), sum(tot))
        dser = []
        for v in VS[1:]:
            dv, de = diff(ser[V0], ser[v]); dser.append(dict(label=f"{SHORT.get(v, v)} − {SHORT.get(V0, V0)}", color=COL[v], v=dv, e=de))
        panels.append(line(f"Efficiency, {t} particles (pT > 1 GeV)", x, E, [ser[v] for v in VS], "%", 60 if x == "eta" else 70, 100,
                           col="L" if s == "hs" else "D"))
        panels.append(line(f"Efficiency difference to {SHORT.get(V0, V0)}, {t} [% points]", x, E, dser, "%", None, None, col="L" if s == "hs" else "D"))
    figs[f"eff_{x}"] = panels
for x, E in (("eta", ETA), ("pt", PTF)):
    panels = []
    ser = {}
    for v in VS:
        val, err, tot, pas = eff(G(v, "all", f"FakeRate/fakerate_vs_{x}"), E, x == "eta", minn=100)
        ser[v] = dict(label=LAB.get(v, v), color=COL[v], v=val, e=err, n=[int(z) for z in tot])
        summ[f"fake {v}"] = (sum(pas), sum(tot))
    panels.append(line("Fake rate (truthMatchProbability < 0.5), % of selected tracks", x, E, [ser[v] for v in VS], "%", 0, None))
    ser = {}
    for v in VS:
        val, err, tot, pas = eff(G(v, "all", f"Duplicate/duplicate_rate_vs_{x}"), ETA if x == "eta" else PT, x == "eta")
        ser[v] = dict(label=LAB.get(v, v), color=COL[v], v=val, e=err, n=[int(z) for z in tot])
        summ[f"dup {v}"] = (sum(pas), sum(tot))
    panels.append(line("Duplicate rate, % of particles with > 1 matched track", x, ETA if x == "eta" else PT, [ser[v] for v in VS], "%", 0, None))
    figs[f"fake_{x}"] = panels
# resolutions and pulls vs |eta| (hard-scatter matched primaries)
RP = [("d0", "d0", "µm", 1000), ("z0", "z0", "µm", 1000), ("qoverp", "q/p", "", 1), ("ptqopt", "q/pT) · pT (", "", 1),
      ("theta", "θ", "mrad", 1000), ("phi", "φ", "mrad", 1000)]
res, pw, pm = [], [], []
for k, name, u, sc in RP:
    ser = []
    for v in VS:
        val, err = width2d(G(v, "hs", f"Matched/Resolutions/Primary/resHelper_eta_{k}"), ETAF, sc)
        ser.append(dict(label=LAB.get(v, v), color=COL[v], v=val, e=err))
    if k != "qoverp": res.append(line(f"σ({name}){' [' + u + ']' if u else ''}", "eta", ETAF, ser, u or "", 0, None))
    if k == "ptqopt": continue
    ser, ser2 = [], []
    for v in VS:
        h = G(v, "hs", f"Matched/Resolutions/Primary/pullHelper_eta_{k}")
        val, err = width2d(h, ETAF); ser.append(dict(label=LAB.get(v, v), color=COL[v], v=val, e=err))
        val, err = width2d(h, ETAF, mean=True); ser2.append(dict(label=LAB.get(v, v), color=COL[v], v=val, e=err))
    pw.append(line(f"Pull width, {name}", "eta", ETAF, ser, "", 0.6, 1.6))
    pm.append(line(f"Pull mean, {name}", "eta", ETAF, ser2, "", -0.4, 0.4, col="D"))
figs["res"] = res; figs["pull"] = pw + pm
# hits and holes vs |eta|, selected tracks
HP = [("nPixelHits", "pixel hits"), ("nSCTHits", "strip hits"), ("nPixelHoles", "pixel holes"), ("nSCTHoles", "strip holes"),
      ("nPixelOutliers", "pixel outliers"), ("nSCTOutliers", "strip outliers"), ("nPixelSharedHits", "pixel shared hits"), ("nSCTSharedHits", "strip shared hits")]
hp = []
for k, name in HP:
    ser = []
    for v in VS:
        val, err = prof(G(v, "all", f"Selected/HitsOnTracks/{k}_vs_eta"), ETAF)
        ser.append(dict(label=LAB.get(v, v), color=COL[v], v=val, e=err))
        h = G(v, "all", f"Selected/HitsOnTracks/{k}"); summ[f"{k} {v}"] = (h.GetMean(), h.GetEntries())
    hp.append(line(f"Mean {name} per track", "eta", ETAF, ser, "", 0, None, col="L" if "Shared" not in k and "Outlier" not in k else "D"))
figs["hits"] = hp
# LRT: fakes and track counts from lrtfakes.py (InDetLargeD0TrackParticles, truthMatchProbability < 0.5 = fake)
LF = os.path.join(D, os.environ.get("LRTJSON", "lrtfakes.json"))
if os.path.exists(LF):
    L = json.load(open(LF)); LE = L["edges"]; XL.update(d0="|d0| [mm]")
    lp = []
    for ax in ("eta", "d0", "pt"):
        ser, cnt = [], []
        for v in VS:
            if v not in L["data"]: continue
            B = L["data"][v]["R"]["lrt"][ax]; nev = L["data"][v]["nev"]
            val = [round(100 * f / n, 4) if n >= 100 else None for n, f in B]
            err = [round(100 * math.sqrt(max(f / n * (1 - f / n), 1 / n) / n), 4) if n >= 100 else None for n, f in B]
            ser.append(dict(label=LAB.get(v, v), color=COL[v], v=val, e=err, n=[n for n, f in B]))
            cnt.append(dict(label=LAB.get(v, v), color=COL[v], v=[round(n / nev, 2) for n, f in B], e=None))
            tot = sum(n for n, f in B); fk = sum(f for n, f in B)
            if ax == "eta": summ[f"lrt fake {v}"] = (fk, tot); summ[f"lrt real {v}"] = (tot - fk, tot)
        lp.append(line(f"LRT fake rate, % of LRT tracks, vs {XL[ax]}", ax, LE[ax], ser, "%", 0, None))
        lp.append(line(f"LRT tracks per event vs {XL[ax]}", ax, LE[ax], cnt, "", 0, None, col="D"))
    figs["lrt"] = lp
NOTES = {
    "eff_eta": "IDPVM, truth pT > 1 GeV, |η| < 4, matched at truthMatchProbability > 0.5. Difference errors add both samples in quadrature; the samples share events, so they are conservative. HS + PU panels folded below.",
    "eff_pt": "As above, vs truth pT.",
    "fake_eta": "All selected tracks (IDPVM selection), HS + PU truth. Duplicate rate vs truth |η|.",
    "fake_pt": "Fake rate vs track pT, duplicate rate vs truth pT.",
    "res": "Hard-scatter matched primaries. Width: iterative RMS within ±3 RMS of the residual, folded over ±η, 0.25 bins. σ(q/pT) · pT is the relative pT resolution.",
    "pull": "Same tracks. Pull means folded below.",
    "lrt": "InDetLargeD0TrackParticles, all tracks; fake = truthMatchProbability < 0.5 or no truth link. Tracks per event folded below.",
    "hits": "All selected tracks, IDPVM summary counts; holes are as the track summary reports them, i.e. after the edge border. Outliers and shared hits folded below.",
}
MORE = {"eff_eta": "Hard scatter + pile-up", "eff_pt": "Hard scatter + pile-up", "pull": "Pull means",
        "hits": "Outliers and shared hits", "lrt": "LRT tracks per event"}
json.dump(dict(figs=figs, notes=NOTES, more=MORE), open(OUT, "w"), separators=(",", ":"))
for k, (a, b) in sorted(summ.items()):
    print(f"{k:28s} {a:12.4f} {b:12.0f}" + (f"  {100*a/b:.3f}%" if b and a <= b and not k.startswith("n") else ""))
