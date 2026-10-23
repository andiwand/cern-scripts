import csv, collections, json, sys, statistics
base = sys.argv[1]
rows = list(csv.DictReader(open(base)))
modules = {int(r["index"]): r for r in csv.DictReader(open(base + ".modules.csv"))}
by = collections.defaultdict(list)
for r in rows:
    by[r["variant"]].append(r)
num = ["steps","ix_stepper","ix_navother","ix_initialize","ix_reached","ix_g1layers","ix_g1surfaces","ix_g1boundaries","ix_g3portals","ix_g3surfaces","ix_g3other","volume_switches","renavigations","reached_sensitive","reached_material","reached_structure"]
def nav(r):
    return sum(int(r[k]) for k in ["ix_navother","ix_initialize","ix_reached","ix_g1layers","ix_g1surfaces","ix_g1boundaries","ix_g3portals","ix_g3surfaces","ix_g3other"])
def mean(rs, f):
    return sum(f(r) for r in rs) / len(rs)
order = ["gen1","gen1-2ap","gen3-abut","gen3-window","gen3-floor1","gen3-tryall","gen3-sandwich"]
order = [v for v in order if v in by]
print("== per track means, all pT")
cols = ["nav_total","stepper","total","steps","volsw","renav","g1layers","g1surf","g1bnd","g3portal","g3surf","navother","sens","mat","struct"]
print("variant".ljust(14) + "".join(c.rjust(9) for c in cols))
summary = {}
for v in order:
    rs = by[v]
    vals = [mean(rs, nav), mean(rs, lambda r: int(r["ix_stepper"])), mean(rs, lambda r: nav(r)+int(r["ix_stepper"])), mean(rs, lambda r: int(r["steps"])), mean(rs, lambda r: int(r["volume_switches"])), mean(rs, lambda r: int(r["renavigations"])),
            mean(rs, lambda r: int(r["ix_g1layers"])), mean(rs, lambda r: int(r["ix_g1surfaces"])), mean(rs, lambda r: int(r["ix_g1boundaries"])), mean(rs, lambda r: int(r["ix_g3portals"])), mean(rs, lambda r: int(r["ix_g3surfaces"])), mean(rs, lambda r: int(r["ix_navother"])),
            mean(rs, lambda r: int(r["reached_sensitive"])), mean(rs, lambda r: int(r["reached_material"])), mean(rs, lambda r: int(r["reached_structure"]))]
    summary[v] = dict(zip(cols, [round(x, 2) for x in vals]))
    print(v.ljust(14) + "".join(f"{x:9.1f}" for x in vals))
print("\n== navigator-side intersections per track by pT")
pts = sorted({float(r["pt"]) for r in rows})
print("variant".ljust(14) + "".join(f"{pt:8.1f}" for pt in pts) + "   (GeV)")
bypt = {}
for v in order:
    line = []
    for pt in pts:
        rs = [r for r in by[v] if float(r["pt"]) == pt]
        line.append(mean(rs, nav))
    bypt[v] = dict(zip([pt for pt in pts], [round(x,2) for x in line]))
    print(v.ljust(14) + "".join(f"{x:8.1f}" for x in line))
print("\n== steps per track by pT")
for v in order:
    print(v.ljust(14) + "".join(f"{mean([r for r in by[v] if float(r['pt'])==pt], lambda r: int(r['steps'])):8.1f}" for pt in pts))
print("\n== navigator-side intersections per track by |eta| bin")
etabins = [(0,0.5),(0.5,1.0),(1.0,1.5),(1.5,2.0),(2.0,2.5)]
byeta = {}
print("variant".ljust(14) + "".join(f"{a:.1f}-{b:.1f}".rjust(9) for a,b in etabins))
for v in order:
    line = [mean([r for r in by[v] if a <= abs(float(r["eta"])) < b], nav) for a,b in etabins]
    byeta[v] = [round(x,2) for x in line]
    print(v.ljust(14) + "".join(f"{x:9.1f}" for x in line))
print("\n== hit sets vs gen1")
g1 = {r["track"]: set(r["hits"].split(";")) - {""} for r in by["gen1"]}
hitdiff = {}
for v in order:
    lost = collections.Counter(); gained = collections.Counter(); same = 0; lostpt = collections.Counter(); ntr = collections.Counter()
    for r in by[v]:
        h = set(r["hits"].split(";")) - {""}
        ref = g1[r["track"]]
        if h == ref: same += 1
        for m in ref - h:
            md = modules[int(m)]; lost[(md["subsystem"], md["kind"])] += 1; lostpt[float(r["pt"])] += 1
        for m in h - ref:
            md = modules[int(m)]; gained[(md["subsystem"], md["kind"])] += 1
        ntr[float(r["pt"])] += 1
    tot_ref = sum(len(s) for s in g1.values())
    print(f"{v}: identical hit set on {same}/{len(by[v])} tracks; lost {sum(lost.values())} of {tot_ref} gen1 hits ({100*sum(lost.values())/tot_ref:.2f}%), gained {sum(gained.values())}")
    if lost: print("   lost by (subsystem,kind):", dict(lost))
    if gained: print("   gained by (subsystem,kind):", dict(gained))
    if lost: print("   lost per track by pT:", {pt: round(lostpt[pt]/ntr[pt], 3) for pt in sorted(ntr)})
    hitdiff[v] = {"same": same, "n": len(by[v]), "lost": sum(lost.values()), "gained": sum(gained.values()), "ref": tot_ref,
                  "lost_by": {f"{k[0]}/{k[1]}": c for k, c in lost.items()}, "gained_by": {f"{k[0]}/{k[1]}": c for k, c in gained.items()},
                  "lost_per_track_by_pt": {str(pt): round(lostpt[pt]/ntr[pt], 3) for pt in sorted(ntr)}}
json.dump({"summary": summary, "by_pt": bypt, "by_eta": byeta, "hits": hitdiff, "n_tracks": len(by[order[0]])}, open(base + ".summary.json", "w"), indent=1)

print("\n== gen3-abut lost hits by (subsystem, kind, layer) and pT")
lost = collections.Counter(); seen = collections.Counter()
for r in by[[v for v in order if v.startswith("gen3")][0]]:
    h = set(r["hits"].split(";")) - {""}
    ref = g1[r["track"]]
    pt = float(r["pt"])
    for m in ref:
        md = modules[int(m)]; seen[(md["subsystem"], md["kind"], md["layer"], pt)] += 1
    for m in ref - h:
        md = modules[int(m)]; lost[(md["subsystem"], md["kind"], md["layer"], pt)] += 1
keys = sorted({k[:3] for k in seen}, key=lambda k: (k[0], k[1], int(k[2])))
pts_ = sorted({k[3] for k in seen})
print("layer".ljust(26) + "".join(f"{pt:>12.1f}" for pt in pts_) + "   lost/seen (%)")
bylayer = {}
for k in keys:
    cells = []
    for pt in pts_:
        s_ = seen[(k[0], k[1], k[2], pt)]; l_ = lost[(k[0], k[1], k[2], pt)]
        cells.append(f"{l_}/{s_} ({100*l_/s_:.0f})" if s_ else "-")
        bylayer.setdefault(f"{k[0]}/{k[1]}/{k[2]}", {})[str(pt)] = [l_, s_]
    print(f"{k[0]}/{k[1]}/{k[2]}".ljust(26) + "".join(c.rjust(12) for c in cells))
d = json.load(open(base + ".summary.json")); d["lost_by_layer"] = bylayer
json.dump(d, open(base + ".summary.json", "w"), indent=1)
