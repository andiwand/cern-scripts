import sys, uproot, numpy as np, collections
for d in sys.argv[1:]:
    t = uproot.open(f"{d}/tracksummary_ckf.root")["tracksummary"]
    vols = t["measurementVolume"].array(library="np"); lays = t["measurementLayer"].array(library="np")
    cls = t["trackClassification"].array(library="np")
    first, last, cnt = collections.Counter(), collections.Counter(), 0
    for ev in range(len(vols)):
        for v, l, c in zip(vols[ev], lays[ev], cls[ev]):
            v, l = list(v), list(l)
            if c != 1 or not v: continue
            cnt += 1
            first[(v[0], l[0])] += 1; last[(v[-1], l[-1])] += 1
    print(d.split("/")[-1], "matched", cnt, "first", first.most_common(4), "last", last.most_common(4))
