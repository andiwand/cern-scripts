#!/usr/bin/env python3
"""Table of the IDPVM headline numbers for several runs: cmpidpvm.py <dir> ..."""
import sys, ROOT
ROOT.gROOT.SetBatch(True)
KEYS=[("effLoose","SquirrelPlots/Tracks/Efficiency/efficiency_vs_eta"),
      ("effTight","SquirrelPlots/TightPrimary/Tracks/Efficiency/efficiency_vs_eta"),
      ("d0res","SquirrelPlots/Tracks/Matched/Resolutions/Primary/resolution_vs_eta_d0"),
      ("z0res","SquirrelPlots/Tracks/Matched/Resolutions/Primary/resolution_vs_eta_z0"),
      ("phires","SquirrelPlots/Tracks/Matched/Resolutions/Primary/resolution_vs_eta_phi"),
      ("thres","SquirrelPlots/Tracks/Matched/Resolutions/Primary/resolution_vs_eta_theta"),
      ("qoptres","SquirrelPlots/Tracks/Matched/Resolutions/Primary/resolution_vs_eta_qopt"),
      ("d0pull","SquirrelPlots/Tracks/Matched/Resolutions/Primary/pullwidth_vs_eta_d0"),
      ("z0pull","SquirrelPlots/Tracks/Matched/Resolutions/Primary/pullwidth_vs_eta_z0"),
      ("phipull","SquirrelPlots/Tracks/Matched/Resolutions/Primary/pullwidth_vs_eta_phi"),
      ("pixHit","SquirrelPlots/Tracks/Selected/HitsOnTracks/nPixelHits_vs_eta"),
      ("sctHit","SquirrelPlots/Tracks/Selected/HitsOnTracks/nSCTHits_vs_eta"),
      ("pixHole","SquirrelPlots/Tracks/Selected/HitsOnTracks/nPixelHoles_vs_eta"),
      ("sctHole","SquirrelPlots/Tracks/Selected/HitsOnTracks/nSCTHoles_vs_eta")]
def avg(f,p):
    h=f.Get(p)
    if not h: return float('nan')
    if isinstance(h,ROOT.TEfficiency):
        t=h.GetTotalHistogram(); q=h.GetPassedHistogram()
        T=sum(t.GetBinContent(i) for i in range(1,t.GetNbinsX()+1))
        P=sum(q.GetBinContent(i) for i in range(1,q.GetNbinsX()+1))
        return P/T if T else float('nan')
    tot=n=0.
    for i in range(1,h.GetNbinsX()+1):
        try: e=h.GetBinEntries(i)
        except Exception: e=1. if h.GetBinContent(i) else 0.
        if e>0: tot+=h.GetBinContent(i)*e; n+=e
    return tot/n if n else float('nan')
dirs=sys.argv[1:]
rows={d:{k:avg(ROOT.TFile.Open(f"{d}/idpvm.root"),p) for k,p in KEYS} for d in dirs}
names=[d.replace("mu_pt10_","") for d in dirs]
print(f"{'':9s}"+"".join(f"{n:>11s}" for n in names))
for k,_ in KEYS:
    print(f"{k:9s}"+"".join(f"{rows[d][k]:11.4g}" for d in dirs))
