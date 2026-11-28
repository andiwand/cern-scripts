import sys, numpy as np, uproot
for d in sys.argv[1:]:
    c = uproot.open(f"{d}/clusters.root")["clusters"].arrays(["event_nr", "volume_id", "layer_id", "clus_size", "clus_gx", "clus_gy", "clus_gz"], library="np")
    h = uproot.open(f"{d}/hits.root")["hits"].arrays(["event_id", "volume_id", "layer_id", "tx", "ty", "tz", "barcode_generation", "barcode_vertex_secondary"], library="np")
    nev = len(np.unique(c["event_nr"]))
    m = (c["volume_id"] == 17) & (c["layer_id"] == 2)
    r = np.median(np.hypot(c["clus_gx"][m], c["clus_gy"][m])); z = np.abs(c["clus_gz"][m]); size = c["clus_size"][m]
    hm = (h["volume_id"] == 17) & (h["layer_id"] == 2); hz = np.abs(h["tz"][hm])
    sec = (h["barcode_generation"][hm] > 0) | (h["barcode_vertex_secondary"][hm] > 0)
    parts = []
    for lo, hi in [(0, 50), (250, 500)]:
        sel = (z >= lo) & (z < hi); area = 2 * np.pi * r * 2 * (hi - lo) / 100.0
        hs = (hz >= lo) & (hz < hi)
        parts.append(f"|z| {lo}-{hi}: hits {hs.sum()/nev/area:5.1f} clusters {sel.sum()/nev/area:5.1f} fired pixels {size[sel].sum()/nev/area:6.1f} /cm2 (mean size {size[sel].mean():.1f}, secondaries {100*sec[hs].mean():.0f}%)")
    print(f"{d}: r={r:.1f} mm, events {nev}\n   " + "\n   ".join(parts))
