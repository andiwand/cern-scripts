# usage: effsum.py <dirA> <dirB>   integrated + binned eff/fake/dup from idpvm.root
import ROOT, sys, math
A,B=sys.argv[1:3]
def tot(f,n):
    e=f.Get("SquirrelPlots/Tracks/"+n)
    p=e.GetPassedHistogram(); t=e.GetTotalHistogram()
    return p, t
def line(lbl,pa,ta,pb,tb):
    ea=pa/ta if ta else 0; eb=pb/tb if tb else 0
    err=math.sqrt(ea*(1-ea)/ta+eb*(1-eb)/tb) if ta and tb else 0
    print(f"{lbl:22s} {ea:8.4f} ({int(pa)}/{int(ta)})  {eb:8.4f} ({int(pb)}/{int(tb)})  diff {eb-ea:+.4f} +- {err:.4f}")
fa=ROOT.TFile.Open(A+"/idpvm.root"); fb=ROOT.TFile.Open(B+"/idpvm.root")
print(f"{'':22s} {A:>8s}  {B:>8s}")
for n,var in [("Efficiency/efficiency_vs_eta","eta"),("FakeRate/fakerate_vs_eta","eta"),("Duplicate/duplicate_rate_vs_eta","eta"),
              ("Efficiency/efficiency_vs_pt","pt"),("FakeRate/fakerate_vs_pt","pt"),("Duplicate/duplicate_rate_vs_pt","pt")]:
    pa,ta=tot(fa,n); pb,tb=tot(fb,n)
    print("==",n)
    line("integral",pa.Integral(0,pa.GetNbinsX()+1),ta.Integral(0,ta.GetNbinsX()+1),pb.Integral(0,pb.GetNbinsX()+1),tb.Integral(0,tb.GetNbinsX()+1))
    nb=ta.GetNbinsX(); step=max(1,nb//8) if var=="eta" else 1
    if var=="eta":
        for i in range(1,nb+1,step):
            j=min(nb,i+step-1)
            line(f"{ta.GetXaxis().GetBinLowEdge(i):+.1f}..{ta.GetXaxis().GetBinUpEdge(j):+.1f}",pa.Integral(i,j),ta.Integral(i,j),pb.Integral(i,j),tb.Integral(i,j))
    else:
        for i in range(1,nb+1):
            if ta.GetBinContent(i)<50: continue
            line(f"{ta.GetXaxis().GetBinLowEdge(i):.1f}..{ta.GetXaxis().GetBinUpEdge(i):.1f}",pa.GetBinContent(i),ta.GetBinContent(i),pb.GetBinContent(i),tb.GetBinContent(i))
