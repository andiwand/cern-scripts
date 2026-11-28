import sys, pathlib, collections
import numpy as np, awkward as ak, uproot
src = open("gain.py").read().split("d = pathlib.Path(sys.argv[1])")[0]
exec(src)
d = pathlib.Path(sys.argv[1])
inner = innermost_pixel_layer(d / "hits.root")
seeds = tracks(d / "tracksummary_seeds.root", d / "trackstates_seeds.root", inner)

def fate(v):
    """the best fate of a particle's tracks"""
    out = {}
    for p, ts in v.items():
        if any(ok and onl for ok, onl, _ in ts): out[p] = "ok"
        elif any(ok for ok, _, _ in ts): out[p] = "missing"
        else: out[p] = "wrong"
    return out

names = [a for a in sys.argv[2:] if not a.startswith("--")]
F = {v: fate(tracks(d / v / f"tracksummary_{v}_ambi.root", d / v / f"trackstates_{v}_ambi.root", inner)) for v in names}
particles = set(seeds) | set().union(*[set(f) for f in F.values()])

# the selection of `particles_selected`: vertex, charge, pT, eta and 9
# measurements, counted here as sim hits
A = uproot.open(d / "particles_simulation.root")["particles"].arrays(
    ["event_id", "vx", "vy", "vz", "q", "pt", "eta"] + ID)
P = {f: ak.to_numpy(ak.flatten(A[f])) for f in A.fields if f != "event_id"}
P["event_id"] = ak.to_numpy(ak.flatten(ak.broadcast_arrays(A.event_id, A.pt)[0]))
pk = key([P[i].astype(np.int64) for i in ID])
h = uproot.open(d / "hits.root")["hits"].arrays(["event_id"] + [f"barcode_{i}" for i in ID], library="np")
hk = key([h[f"barcode_{i}"].astype(np.int64) for i in ID])
nHits = collections.Counter(zip(h["event_id"].tolist(), hk.tolist()))
sel = (np.hypot(P["vx"], P["vy"]) < 24) & (np.abs(P["vz"]) < 1000) & (P["q"] != 0) & (P["pt"] >= 1.0) & (np.abs(P["eta"]) <= 3.0)
selected = {(int(e), int(k)) for e, k, ok in zip(P["event_id"], pk, sel) if ok and nHits[(int(e), int(k))] >= 9}
print(d.name, "selected particles (rebuilt):", len(selected))
particles &= selected if "--all" not in sys.argv else particles
print(d.name, "particles with a seed or a track:", len(particles), " without a majority seed:", len(particles - set(seeds)))
order = ["ok", "missing", "wrong", "none"]
for v in names:
    c = collections.Counter(F[v].get(p, "none") for p in particles)
    print(f"  {v:18s} " + "  ".join(f"{k}={c[k]}" for k in order))
for a, b in zip(names[0::2], names[1::2]):
    print(f"  cross table, rows {a}, columns {b}")
    t = collections.Counter((F[a].get(p, "none"), F[b].get(p, "none")) for p in particles)
    print("    " + " " * 9 + "".join(f"{k:>9s}" for k in order))
    for r in order:
        print(f"    {r:9s}" + "".join(f"{t[(r, k)]:9d}" for k in order))
