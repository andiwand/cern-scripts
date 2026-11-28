import sys, uproot, numpy as np
def matched(d, stage):
    m = uproot.open(f"{d}/performance_finding_{stage}.root")["matchingdetails"].arrays(library="np")
    keys = list(zip(m["event_nr"], m["particle_id_vertex_primary"], m["particle_id_vertex_secondary"], m["particle_id_particle"], m["particle_id_generation"], m["particle_id_sub_particle"]))
    return {k for k, ok in zip(keys, m["matched"]) if ok}, {k for k in keys}
ref, cand = sys.argv[1], sys.argv[2]
for stage in ("ckf", "ambi"):
    a, alla = matched(ref, stage); b, allb = matched(cand, stage)
    print(stage, "ref matched", len(a), "cand matched", len(b), "lost", len(a - b), "gained", len(b - a))
p = uproot.open(f"{sys.argv[3]}/particles_selected.root")["particles"].arrays(["event_id","vertex_primary","vertex_secondary","particle","generation","sub_particle","pt","eta"], library="np")
info = {}
for e in range(len(p["event_id"])):
    for i in range(len(p["pt"][e])):
        info[(p["event_id"][e], p["vertex_primary"][e][i], p["vertex_secondary"][e][i], p["particle"][e][i], p["generation"][e][i], p["sub_particle"][e][i])] = (p["pt"][e][i], p["eta"][e][i])
a, _ = matched(ref, "ambi"); b, _ = matched(cand, "ambi")
lost = [info[k] for k in a - b if k in info]
alln = [info[k] for k in a if k in info]
eta = np.abs(np.array([x[1] for x in lost])); etaAll = np.abs(np.array([x[1] for x in alln]))
bins = [0, 0.5, 1, 1.5, 2, 2.5, 3]
print("lost fraction by |eta|:", np.round(np.histogram(eta, bins)[0] / np.maximum(np.histogram(etaAll, bins)[0], 1), 4))
pt = np.array([x[0] for x in lost]); ptAll = np.array([x[0] for x in alln])
pb = [1, 2, 5, 10, 100]
print("lost fraction by pT:", np.round(np.histogram(pt, pb)[0] / np.maximum(np.histogram(ptAll, pb)[0], 1), 4))
