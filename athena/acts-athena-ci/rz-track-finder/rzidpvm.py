#!/usr/bin/env python3
"""Compare IDPVM output between two reconstructions (CKF vs the RZ finder).

usage: rzidpvm.py <a/idpvm.root> <b/idpvm.root> [--all]
"""
import sys
import ROOT

ROOT.gROOT.SetBatch(True)

# efficiency and fake rate are TEfficiency-like TProfiles in [0, 1];
# resolution_vs_* are the fitted widths per bin
GROUPS = [
    ("efficiency (all truth)", [
        "SquirrelPlots/Tracks/Efficiency/efficiency_vs_eta",
        "SquirrelPlots/Tracks/Efficiency/efficiency_vs_pt",
        "SquirrelPlots/Tracks/Efficiency/efficiency_vs_phi",
    ]),
    ("efficiency (tight primary)", [
        "SquirrelPlots/TightPrimary/Tracks/Efficiency/efficiency_vs_eta",
        "SquirrelPlots/TightPrimary/Tracks/Efficiency/efficiency_vs_pt",
    ]),
    ("fake rate (all)", [
        "SquirrelPlots/Tracks/FakeRate/fakerate_vs_eta",
        "SquirrelPlots/Tracks/FakeRate/fakerate_vs_pt",
        "SquirrelPlots/Tracks/FakeRate/fakerate_vs_mu",
    ]),
    ("fake rate (tight primary)", [
        "SquirrelPlots/TightPrimary/Tracks/FakeRate/fakerate_vs_eta",
        "SquirrelPlots/TightPrimary/Tracks/FakeRate/fakerate_vs_pt",
    ]),
    ("resolution vs eta (primary)", [
        f"SquirrelPlots/Tracks/Matched/Resolutions/Primary/resolution_vs_eta_{v}"
        for v in ("d0", "z0", "phi", "theta", "pt", "qopt")
    ]),
    ("resolution vs pt (primary)", [
        f"SquirrelPlots/Tracks/Matched/Resolutions/Primary/resolution_vs_pt_{v}"
        for v in ("d0", "z0", "phi", "theta", "pt", "qopt")
    ]),
    ("pull width vs eta (primary)", [
        f"SquirrelPlots/Tracks/Matched/Resolutions/Primary/pullwidth_vs_eta_{v}"
        for v in ("d0", "z0", "phi", "theta", "qopt")
    ]),
    ("hits and holes", [
        "SquirrelPlots/Tracks/Selected/HitsOnTracks/nPixelHits_vs_eta",
        "SquirrelPlots/Tracks/Selected/HitsOnTracks/nSCTHits_vs_eta",
        "SquirrelPlots/Tracks/Selected/HitsOnTracks/nPixelHoles_vs_eta",
        "SquirrelPlots/Tracks/Selected/HitsOnTracks/nSCTHoles_vs_eta",
    ]),
]


def get(f, path):
    obj = f.Get(path)
    return obj if obj else None


def average(hist):
    """One number per histogram.

    For a TEfficiency that is the integrated efficiency — passed over total
    summed across bins, which is what "the efficiency" usually means — and for
    a profile the mean over the bins that carry entries, so that empty bins do
    not drag a resolution curve down.
    """
    if hist.InheritsFrom("TEfficiency"):
        total = hist.GetTotalHistogram()
        passed = hist.GetPassedHistogram()
        nt = sum(total.GetBinContent(i) for i in range(1, total.GetNbinsX() + 1))
        npass = sum(passed.GetBinContent(i)
                    for i in range(1, passed.GetNbinsX() + 1))
        filled = sum(1 for i in range(1, total.GetNbinsX() + 1)
                     if total.GetBinContent(i))
        return (npass / nt if nt else float("nan")), filled

    total, n = 0.0, 0
    profile = hist.InheritsFrom("TProfile")
    for i in range(1, hist.GetNbinsX() + 1):
        filled = hist.GetBinEntries(i) if profile else hist.GetBinContent(i) != 0
        if filled:
            total += hist.GetBinContent(i)
            n += 1
    return (total / n if n else float("nan")), n


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    fa, fb = (ROOT.TFile.Open(p) for p in sys.argv[1:3])
    if not fa or fa.IsZombie() or not fb or fb.IsZombie():
        print("could not open both files")
        return 1

    print(f"a = {sys.argv[1]}\nb = {sys.argv[2]}\n")
    for label, paths in GROUPS:
        rows = []
        for path in paths:
            ha, hb = get(fa, path), get(fb, path)
            if ha is None or hb is None:
                continue
            a, na = average(ha)
            b, nb = average(hb)
            if na == 0 or nb == 0:
                continue
            delta = 100.0 * (b / a - 1.0) if a else float("nan")
            rows.append((path.split("/")[-1], a, b, delta, na, nb))
        if not rows:
            continue
        print(f"=== {label}")
        for name, a, b, delta, na, nb in rows:
            print(f"  {name:28s} a={a:12.6g}  b={b:12.6g}  {delta:+8.1f}%"
                  f"   bins {na}/{nb}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
