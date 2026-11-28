import sys, uproot, numpy as np
for d in sys.argv[1:]:
    t = uproot.open(f"{d}/tracksummary_ambi.root")["tracksummary"]
    a = {k: np.concatenate(t[k].array(library="np")) for k in ["nMeasurements", "nMajorityHits", "nHoles", "nOutliers", "trackClassification"]}
    pur = a["nMajorityHits"] / np.maximum(a["nMeasurements"], 1)
    m = a["trackClassification"] == 1
    print(f"{d.split('/')[-1]:10s} tracks {len(pur)} matched {m.mean():.4f} purity<1 {(pur < 1).mean():.4f} purity<0.5 {(pur < 0.5).mean():.4f} nMeas {a['nMeasurements'].mean():.2f} holes {a['nHoles'].mean():.2f} outl {a['nOutliers'].mean():.2f}")
