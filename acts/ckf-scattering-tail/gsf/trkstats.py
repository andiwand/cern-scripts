import sys, uproot, numpy as np
for d in sys.argv[1:]:
    t = uproot.open(f"{d}/tracksummary_ckf.root")["tracksummary"]
    a = {k: np.concatenate(t[k].array(library="np")) for k in ["nMeasurements","nHoles","nOutliers","chi2Sum","NDF","res_eLOC0_fit","res_eQOP_fit","pull_eQOP_fit","pull_eLOC0_fit","trackClassification","hasFittedParams"]}
    f = a["hasFittedParams"].astype(bool)
    q = lambda x: np.quantile(np.abs(x[f & np.isfinite(x)]), 0.68)
    print(d.split("/")[-1], f"tracks {len(f)}", f"nMeas {a['nMeasurements'].mean():.2f}", f"holes {a['nHoles'].mean():.2f}", f"outl {a['nOutliers'].mean():.2f}",
          f"chi2/ndf {np.median(a['chi2Sum']/np.maximum(a['NDF'],1)):.2f}", f"classes {np.bincount(a['trackClassification'].astype(int))}",
          f"d0res {q(a['res_eLOC0_fit']):.4f} qopres {q(a['res_eQOP_fit']):.5f} pull d0 {q(a['pull_eLOC0_fit']):.2f} pull qop {q(a['pull_eQOP_fit']):.2f}")
