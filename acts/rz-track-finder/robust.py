import sys, uproot, numpy as np
mad=lambda v: 1.4826*np.median(np.abs(v-np.median(v)))
for d in sys.argv[1:]:
    tag="ckf" if "ckf" in d else "rz"
    t=uproot.open(f"{d}/tracksummary_{tag}.root")["tracksummary"]
    keys=["pull_eLOC0_fit","pull_eLOC1_fit","pull_ePHI_fit","pull_eTHETA_fit","pull_eQOP_fit","res_eLOC0_fit","res_eLOC1_fit"]
    a=t.arrays(keys,library="np")
    for k in keys:
        v=np.concatenate(a[k]); a[k]=v[np.isfinite(v)]
    print(f"{d:28s} robust pull widths d0/z0/phi/theta/qop:", [round(float(mad(a[k])),2) for k in keys[:5]], " tails |pull|>4:", [round(float((np.abs(a[k])>4).mean()),4) for k in keys[:5]], " robust res d0 %.1f um z0 %.1f um"%(mad(a["res_eLOC0_fit"])*1e3, mad(a["res_eLOC1_fit"])*1e3))
