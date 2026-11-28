import sys, uproot, numpy as np, collections
def matched(d):
    m = uproot.open(f"{d}/performance_finding_ckf.root")["matchingdetails"].arrays(library="np")
    keys = list(zip(m["event_nr"], m["particle_id_vertex_primary"], m["particle_id_vertex_secondary"], m["particle_id_particle"], m["particle_id_generation"], m["particle_id_sub_particle"]))
    return {k for k, ok in zip(keys, m["matched"]) if ok}
ref, cand = sys.argv[1], sys.argv[2]
lost = matched(ref) - matched(cand)
def tracks(d):
    t = uproot.open(f"{d}/tracksummary_ckf.root")["tracksummary"]
    names = ["majorityParticleId_vertex_primary","majorityParticleId_vertex_secondary","majorityParticleId_particle","majorityParticleId_generation","majorityParticleId_sub_particle","nMeasurements","nHoles","nOutliers","trackClassification","measurementVolume"]
    a = t.arrays(names + ["event_nr"], library="np")
    out = collections.defaultdict(list)
    for e in range(len(a["event_nr"])):
        for i in range(len(a["nMeasurements"][e])):
            k = (a["event_nr"][e],) + tuple(a[n][e][i] for n in names[:5])
            out[k].append((a["nMeasurements"][e][i], a["nHoles"][e][i], a["trackClassification"][e][i], list(a["measurementVolume"][e][i])))
    return out
tc, tr = tracks(cand), tracks(ref)
have = [k for k in lost if k in tc]
print("lost", len(lost), "with a candidate track", len(have))
cls = collections.Counter(c for k in have for (_, _, c, _) in tc[k])
print("their classes", cls)
nm = [max(x[0] for x in tc[k]) for k in have]; nr = [max(x[0] for x in tr[k]) for k in have if k in tr]
print("nMeas cand mean", np.mean(nm), "ref mean", np.mean(nr))
vc = collections.Counter(); vr = collections.Counter()
for k in have[:2000]:
    c = max(tc[k], key=lambda x: x[0]); vc.update(set(c[3]))
    if k in tr: r = max(tr[k], key=lambda x: x[0]); vr.update(set(r[3]))
print("volumes with hits, ref vs cand:", {v: (vr[v], vc[v]) for v in sorted(set(vr) | set(vc))})
