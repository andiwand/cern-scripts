#!/usr/bin/env python3
"""Single-particle summary per variant from ana-mu/<sample>/<v>/idpvm_hs.root: efficiency, hits/holes/outliers per track,
q/p and phi pull core width (iterative 3-sigma RMS), pull tail fraction |pull|>3 and >5, q/pT*pT core width.
usage: muana.py <ana dir> <sample> <variant>...  (needs the asetup env for ROOT); split: ETACUT (default 1.0) barrel/endcap"""
import sys, math, os, ROOT
D, S = sys.argv[1:3]; VS = sys.argv[3:]; EC = float(os.environ.get("ETACUT", "1.0"))
def tf(v): return ROOT.TFile.Open(f"{D}/{S}/{v}/idpvm_hs.root")
def proj(h2, lo, hi):
    p = None
    for i in range(1, h2.GetNbinsX() + 1):
        x = abs(h2.GetXaxis().GetBinCenter(i))
        if lo <= x < hi:
            q = h2.ProjectionY(f"_p{id(h2)}_{i}_{lo}", i, i)
            if p is None: p = q.Clone(f"_s{id(h2)}_{lo}_{hi}")
            else: p.Add(q)
    return p
def itrms(h):
    a = h.GetXaxis(); a.SetRange(0, 0); m, r = h.GetMean(), h.GetRMS()
    for _ in range(30):
        a.SetRange(a.FindBin(m - 3 * r), a.FindBin(m + 3 * r)); m2, r2 = h.GetMean(), h.GetRMS()
        if abs(r2 - r) < 1e-4 * r: r, m = r2, m2; break
        r, m = r2, m2
    a.SetRange(0, 0); return r
def tail(h, k):
    n = h.Integral(0, h.GetNbinsX() + 1); a = h.GetXaxis()
    return (h.Integral(0, a.FindBin(-k) - 1) + h.Integral(a.FindBin(k) + 1, h.GetNbinsX() + 1)) / n if n else float("nan")
rows = []
for v in VS:
    f = tf(v); r = {"v": v}
    te = f.Get("SquirrelPlots/Tracks/Efficiency/efficiency_vs_eta")
    p, t = te.GetPassedHistogram().GetEntries(), te.GetTotalHistogram().GetEntries(); r["eff"] = 100 * p / t; r["n"] = t
    for k in ("nPixelHits", "nSCTHits", "nPixelHoles", "nSCTHoles", "nPixelOutliers", "nSCTOutliers"):
        h = f.Get(f"SquirrelPlots/Tracks/Selected/HitsOnTracks/{k}"); r[k] = h.GetMean() if h else float("nan")
    for reg, lo, hi in (("B", 0, EC), ("E", EC, 5)):
        for k in ("qoverp", "phi", "theta"):
            h = proj(f.Get(f"SquirrelPlots/Tracks/Matched/Resolutions/Primary/pullHelper_eta_{k}"), lo, hi)
            r[f"{k}{reg}"] = itrms(h) if h and h.GetEntries() > 30 else float("nan")
            if k == "qoverp" and h:
                r[f"t3{reg}"] = 100 * tail(h, 3); r[f"t5{reg}"] = 100 * tail(h, 5)
        h = proj(f.Get("SquirrelPlots/Tracks/Matched/Resolutions/Primary/resHelper_eta_ptqopt"), lo, hi)
        r[f"res{reg}"] = 100 * itrms(h) if h and h.GetEntries() > 30 else float("nan")
    rows.append(r)
cols = [("eff", "eff%", 7, 2), ("nPixelHits", "pix", 6, 2), ("nSCTHits", "strip", 6, 2), ("nPixelHoles", "pHole", 6, 3), ("nSCTHoles", "sHole", 6, 3),
        ("nPixelOutliers", "pOut", 6, 3), ("nSCTOutliers", "sOut", 6, 3),
        ("qoverpB", "qpB", 6, 3), ("qoverpE", "qpE", 6, 3), ("t3B", "qp>3B%", 7, 2), ("t3E", "qp>3E%", 7, 2), ("t5B", "qp>5B%", 7, 2), ("t5E", "qp>5E%", 7, 2),
        ("phiB", "phiB", 6, 3), ("phiE", "phiE", 6, 3), ("resB", "σpT%B", 6, 2), ("resE", "σpT%E", 6, 2)]
print(f"{S}  N={int(rows[0]['n'])}  barrel |eta|<{EC}")
print(f"{chr(32)*0:5s}" + "".join(f"{c[1]:>{c[2]+1}s}" for c in cols))
for r in rows: print(f"{r['v']:5s}" + "".join(f"{r[c[0]]:{c[2]+1}.{c[3]}f}" for c in cols))
