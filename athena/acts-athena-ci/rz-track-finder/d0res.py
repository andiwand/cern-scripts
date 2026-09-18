#!/usr/bin/env python3
"""Integrated residual and pull widths for several runs, from the 1D histograms.

Uses the iterative-Gaussian core width IDPVM itself fits, so the number is not
one of the sparse per-eta fits.  usage: d0res.py <dir> ...
"""
import sys, ROOT
ROOT.gROOT.SetBatch(True)
BASE="SquirrelPlots/Tracks/Matched/Resolutions/Primary/"
def corewidth(h, nsig=3.0, iters=6):
    if not h or h.GetEntries() < 20: return float('nan'), 0
    lo, hi = h.GetXaxis().GetXmin(), h.GetXaxis().GetXmax()
    mu, sg = h.GetMean(), h.GetRMS()
    for _ in range(iters):
        r = ROOT.TFitResultPtr(h.Fit("gaus", "QNS", "", max(lo, mu-nsig*sg), min(hi, mu+nsig*sg)))
        if int(r) != 0: break
        mu, sg = r.Parameter(1), r.Parameter(2)
    return sg, h.GetEntries()
vars_=["d0","z0","phi","theta"]
print(f"{'':22s}"+"".join(f"{d.replace('mu_pt',''):>13s}" for d in sys.argv[1:]))
for kind,fmt in (("res","%9.3f"),("pull","%9.3f")):
    for v in vars_:
        row=[]
        for d in sys.argv[1:]:
            f=ROOT.TFile.Open(f"{d}/idpvm.root")
            w,n=corewidth(f.Get(BASE+f"{kind}_{v}"))
            scale = 1000. if (kind=="res" and v in ("d0","z0")) else 1.
            row.append(w*scale)
        unit = " [um]" if (kind=="res" and v in ("d0","z0")) else ""
        print(f"{kind+'_'+v+unit:22s}"+"".join(f"{x:13.4g}" for x in row))
