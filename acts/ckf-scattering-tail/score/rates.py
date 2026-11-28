#!/usr/bin/env python3
"""Export ROOT efficiency counters (uproot cannot read these TEfficiency files)."""
import argparse
import json
from pathlib import Path
import ROOT

p = argparse.ArgumentParser()
p.add_argument("run", type=Path)
a = p.parse_args()
result = {}
for mode in ["core15", "tail", "tail80"]:
    f = ROOT.TFile.Open(str(a.run / f"{mode}_ambi_performance.root"))
    result[mode] = {}
    for name in [
        "trackeff_vs_pT",
        "trackeff_vs_eta",
        "fakeRatio_vs_pT",
        "fakeRatio_vs_eta",
    ]:
        eff = f.Get(name)
        passed, total = eff.GetPassedHistogram(), eff.GetTotalHistogram()
        n = total.GetNbinsX()
        result[mode][name] = {
            "edges": [total.GetXaxis().GetBinLowEdge(i) for i in range(1, n + 2)],
            "passed": [passed.GetBinContent(i) for i in range(1, n + 1)],
            "total": [total.GetBinContent(i) for i in range(1, n + 1)],
        }
    f.Close()
(a.run / "rates.json").write_text(json.dumps(result, indent=2) + "\n")
