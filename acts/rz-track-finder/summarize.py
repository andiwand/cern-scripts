#!/usr/bin/env python3
"""Print finding efficiency, fake and duplicate ratios, hits per track, the
perigee pulls and the per-event time of one or more compare.py outputs side by
side.

    summarize.py output/muon-ckf output/muon-rz
"""

import csv
import sys
from pathlib import Path

import numpy as np
import uproot
import ROOT


def efficiency(f, name):
    e = f.Get(name)
    passed = e.GetPassedHistogram().Integral()
    total = e.GetTotalHistogram().Integral()
    return passed / max(total, 1), total


def profile_mean(f, name):
    p = f.Get(name)
    return p.GetMean(2) if p.GetEntries() else float("nan")


def summarize(out: Path):
    tag = "ckf" if (out / "performance_finding_ckf.root").exists() else "rz"
    perf = ROOT.TFile.Open(str(out / f"performance_finding_{tag}.root"))
    row = {"dir": out.name}
    row["eff"], row["particles"] = efficiency(perf, "trackeff_vs_pT")
    row["fake"], row["tracks"] = efficiency(perf, "fakeRatio_vs_pT")
    row["dup"], _ = efficiency(perf, "duplicationRatio_vs_pT")
    row["meas/track"] = profile_mean(perf, "nMeasurements_vs_eta")
    row["holes/track"] = profile_mean(perf, "nHoles_vs_eta")

    summary = uproot.open(out / f"tracksummary_{tag}.root")["tracksummary"]
    arrays = summary.arrays(
        ["pull_eLOC0_fit", "pull_eLOC1_fit", "pull_ePHI_fit", "pull_eTHETA_fit", "pull_eQOP_fit",
         "res_eLOC0_fit", "res_eLOC1_fit", "res_eQOP_fit", "t_pT", "eQOP_fit", "chi2Sum", "NDF"],
        library="np",
    )
    for key in ["pull_eLOC0_fit", "pull_eLOC1_fit", "pull_ePHI_fit", "pull_eTHETA_fit", "pull_eQOP_fit"]:
        v = np.concatenate(arrays[key]) if arrays[key].dtype == object else arrays[key]
        v = v[np.isfinite(v)]
        row[key.replace("pull_e", "pull ").replace("_fit", "")] = f"{v.mean():+.2f}/{v.std():.2f}"
    for key, scale, unit in [("res_eLOC0_fit", 1e3, "um"), ("res_eLOC1_fit", 1e3, "um")]:
        v = np.concatenate(arrays[key]) if arrays[key].dtype == object else arrays[key]
        v = v[np.isfinite(v)]
        row[f"res {key[5:9]} rms {unit}"] = f"{v.std() * scale:.1f}"
    chi2 = np.concatenate(arrays["chi2Sum"]) if arrays["chi2Sum"].dtype == object else arrays["chi2Sum"]
    ndf = np.concatenate(arrays["NDF"]) if arrays["NDF"].dtype == object else arrays["NDF"]
    good = ndf > 0
    row["chi2/ndf"] = f"{np.mean(chi2[good] / ndf[good]):.2f}"

    with open(out / "timing.csv") as f:
        for r in csv.DictReader(f):
            if r["identifier"] in ("Algorithm:TrackFindingAlgorithm", "Algorithm:RzTrackFindingAlgorithm"):
                row["ms/event"] = f"{float(r['time_perevent_s']) * 1e3:.3f}"
    return row


def main():
    rows = [summarize(Path(p)) for p in sys.argv[1:]]
    keys = list(rows[0].keys())
    width = max(len(k) for k in keys)
    for k in keys:
        cells = []
        for r in rows:
            v = r.get(k, "")
            cells.append(f"{v:.4f}" if isinstance(v, float) else str(v))
        print(f"{k:>{width}}  " + "  ".join(f"{c:>18}" for c in cells))


if __name__ == "__main__":
    main()
