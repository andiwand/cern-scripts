import sys, collections, numpy as np, uproot
ID = ["vertex_primary", "vertex_secondary", "particle", "generation", "sub_particle"]
for d in sys.argv[1:]:
    h = uproot.open(f"{d}/hits.root")["hits"].arrays(["event_id", "volume_id", "layer_id", "tpx", "tpy"] + [f"barcode_{i}" for i in ID], library="np")
    m = (h["volume_id"] == 17) & (h["layer_id"] == 2)
    keys = list(zip(h["event_id"][m].tolist(), *[h[f"barcode_{i}"][m].tolist() for i in ID]))
    pt = np.hypot(h["tpx"][m], h["tpy"][m])
    n = collections.Counter(keys)
    per = np.array(list(n.values()))
    lowpt = collections.Counter(k for k, p in zip(keys, pt) if p < 0.2)
    print(f"{d}: particles on layer 0 {len(n)}, hits {len(keys)}; hits per particle: 1: {np.mean(per==1)*100:.1f}%  2: {np.mean(per==2)*100:.1f}%  >=3: {np.mean(per>=3)*100:.2f}% (max {per.max()}); hits with pT<200 MeV: {100*np.mean(pt<0.2):.1f}%")
