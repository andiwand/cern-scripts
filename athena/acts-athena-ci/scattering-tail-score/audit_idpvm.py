#!/usr/bin/env python3
"""Verify exported inclusive efficiency and fakes against official IDPVM (HS + pile-up truth).

usage: audit_idpvm.py RUN_DIR IDPVM_ROOT   RUN_DIR: one run.sh output (rows.tsv); writes RUN_DIR/idpvm-audit.json
"""
import json
from pathlib import Path
import sys
import ROOT
from analyze import load, counts

root = Path(sys.argv[1])
f = ROOT.TFile.Open(sys.argv[2])
assert f and not f.IsZombie()
report = {}
for key, path in [
    ("efficiency", "Efficiency/efficiency_vs_eta"),
    ("fakes", "FakeRate/fakerate_vs_eta"),
]:
    te = f.Get("SquirrelPlots/Tracks/" + path)
    assert te, path
    passed, total = te.GetPassedHistogram(), te.GetTotalHistogram()
    report[key] = dict(
        passed=int(passed.Integral(1, passed.GetNbinsX())),
        total=int(total.Integral(1, total.GetNbinsX())),
        range=[total.GetXaxis().GetXmin(), total.GetXaxis().GetXmax()],
    )
ours = counts(load(root), "none", 0)
report["export"] = ours
assert report["efficiency"]["passed"] == ours["matched"], report
assert report["efficiency"]["total"] == ours["truth"], report
assert report["fakes"]["passed"] == ours["fakes"], report
assert report["fakes"]["total"] == ours["tracks"], report
(root / "idpvm-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
