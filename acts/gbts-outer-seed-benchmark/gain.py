import sys, pathlib, collections
import numpy as np, awkward as ak, uproot
exec(open("analyze.py").read().split("def main():")[0])

def tracks(summaryFile, statesFile, inner):
    """(event, particle) -> list of (innermost hit correct, on true innermost layer, all hits correct)"""
    S = uproot.open(summaryFile)["tracksummary"].arrays(["event_nr", "trackClassification"] + [f"majorityParticleId_{i}" for i in ID])
    T = uproot.open(statesFile)["trackstates"].arrays(["event_nr", "track_nr", "stateType", "volume_id", "layer_id", "t_x", "t_y"] + [f"particle_ids_{i}" for i in ID])
    ev = ak.to_numpy(ak.flatten(ak.broadcast_arrays(S.event_nr, S.trackClassification)[0]))
    cls = ak.to_numpy(ak.flatten(S.trackClassification)); tr = ak.to_numpy(ak.flatten(ak.local_index(S.trackClassification)))
    maj = key([ak.to_numpy(ak.flatten(S[f"majorityParticleId_{i}"])).astype(np.int64) for i in ID])
    sm = {(int(e), int(n)): (int(c), int(m)) for e, n, c, m in zip(ev, tr, cls, maj)}
    PK = key([ak.values_astype(T[f"particle_ids_{i}"], np.int64) for i in ID]); R = np.hypot(T.t_x, T.t_y)
    out = collections.defaultdict(list)
    pkl = PK.tolist(); st_all = T.stateType.tolist(); r_all = R.tolist(); vol_all = T.volume_id.tolist(); lay_all = T.layer_id.tolist()
    for j in range(len(T)):
        e, n = int(T.event_nr[j]), int(T.track_nr[j]); c, m = sm[(e, n)]
        if c not in (1, 2): continue
        st = np.array(st_all[j]); rr = np.array(r_all[j], dtype=float); mi = np.where(st == 0)[0]
        if len(mi) == 0: continue
        i = mi[np.argmin(rr[mi])]
        out[(e, m)].append((m in pkl[j][i], (vol_all[j][i], lay_all[j][i]) == inner.get((e, m)), all(m in pkl[j][k] for k in mi)))
    return out

d = pathlib.Path(sys.argv[1])
inner = innermost_pixel_layer(d / "hits.root")
seeds = tracks(d / "tracksummary_seeds.root", d / "trackstates_seeds.root", inner)
def cat(v):
    if all(not ok for ok, _, _ in v): return "seeds: all wrong inner"
    if any(not ok for ok, _, _ in v): return "seeds: some wrong inner"
    if all(not onl for ok, onl, _ in v): return "seeds: none on true layer 0"
    if all(not pure for _, _, pure in v): return "seeds: wrong outer hit"
    return "seeds: a clean seed"
A, B = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("inner", "outer_top")
var = {"inner": tracks(d / A / f"tracksummary_{A}_ambi.root", d / A / f"trackstates_{A}_ambi.root", inner), "outer_top": tracks(d / B / f"tracksummary_{B}_ambi.root", d / B / f"trackstates_{B}_ambi.root", inner)}
print("comparing", A, "(inner column) with", B, "(outer column)")
table = collections.defaultdict(lambda: collections.Counter())
for p, sv in seeds.items():
    c = cat(sv)
    a, b = p in var["inner"], p in var["outer_top"]
    table[c]["n"] += 1
    table[c][("inner" if a else "-") + "/" + ("outer" if b else "-")] += 1
print(d.name, "particles with a seed", len(seeds))
for c, cnt in sorted(table.items(), key=lambda x: -x[1]["n"]):
    print(f"  {c:30s} n={cnt['n']:6d}  both={cnt['inner/outer']:6d}  inner only={cnt['inner/-']:4d}  outer only={cnt['-/outer']:4d}  neither={cnt['-/-']:4d}")
