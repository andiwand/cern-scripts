#!/usr/bin/env python3
"""Particles legacy finds and ACTS loses (>= 9 own clusters, all pure 5-SP seeds fail): where are the own strip hits
the dropped CKF branch did not collect, where are its holes, what does legacy put on those surfaces.
usage: tracedown.py <trace.txt> <acts dir> <legacy dir> [legacytracks.txt]"""
import sys, os, pickle, collections, math
import numpy as np
trace, dA, dL = sys.argv[1:4]; LT = sys.argv[4] if len(sys.argv) > 4 else None
sys.argv = ["deepdive.py", trace]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deepdive.py")).read().split("def later(a):")[0])

HX = 48.3                                   # strip barrel half width (loc0)
HY = {2: 12.1, 4: 12.1, 6: 24.2, 8: 24.2}   # half length (loc1) per ACTS strip barrel layer: one row of strips

def load(d):
    _, truth = pickle.load(open(os.path.join(d, "splitsum_pu.pkl"), "rb"))
    idx = collections.defaultdict(list)
    for (ev, uid, pt, eta), v in truth.items(): idx[(ev, uid)].append((pt, eta, v[3] is not None))
    return idx
A, L = load(dA), load(dL)
def found(idx, ev, uid, pt, eta):
    c = [f for p, e, f in idx.get((ev, uid), []) if abs(p - pt) < 1. and abs(e - eta) < 1e-3]
    return c[0] if c else None

def plane_point(pix, h):
    """pixel helix intersected with the plane of h -> (loc0, loc1) in that surface frame (None if no helix)"""
    if len(pix) < 3: return None
    P = np.array([p["g"] for p in pix]); xc, yc, R = circle_fit(P[:, :2])
    r = np.hypot(P[:, 0], P[:, 1]); kz = np.polyfit(r, P[:, 2], 1); n = np.cross(h["ex"], h["ey"])
    o = P[np.argmax(r)]; a0 = math.atan2(o[1] - yc, o[0] - xc)
    pt = lambda a: np.array([xc + R * math.cos(a), yc + R * math.sin(a), np.polyval(kz, math.hypot(xc + R * math.cos(a), yc + R * math.sin(a)))])
    s = 1 if math.hypot(*pt(a0 + 1e-3)[:2]) > math.hypot(*pt(a0)[:2]) else -1
    f = lambda a: float(np.dot(pt(a) - h["c"], n))
    a, fa = a0, f(a0)
    for _ in range(2000):
        b = a + s * 2. / R; fb = f(b)
        if fa * fb <= 0:
            for _ in range(40):
                m = 0.5 * (a + b); fm = f(m)
                if fa * fm <= 0: b, fb = m, fm
                else: a, fa = m, fm
            X = pt(0.5 * (a + b)); return float(np.dot(X - h["c"], h["ex"])), float(np.dot(X - h["c"], h["ey"]))
        a, fa = b, fb
    return None

def edge(loc0, loc1, lay):
    return min(HX - abs(loc0), HY.get(lay, 24.2) - abs(loc1))

def surf_rz(h): return math.hypot(h["c"][0], h["c"][1]), h["c"][2]
def at(items, r, z, tol=0.5): return [x for x in items if abs(x["r"] - r) < tol and abs(x["z"] - z) < tol]

# particles: legacy-only, >= 9 own surfaces, all pure 5-SP seeds fail; keep the first failing attempt
P = {}
for a in attempts():
    if a["n"] != 5 or not a["pure"] or a["att"] != 0 or a["T"] is None or a["T"]["pt"] < 1.0: continue
    k = (a["ev"], a["uid"]); p = P.setdefault(k, dict(ok=False, a=None))
    p["ok"] |= a["ntr"] > 0
    if a["ntr"] == 0 and p["a"] is None: p["a"] = a
sel = []
for (ev, uid), p in P.items():
    a = p["a"]
    if p["ok"] or a is None or len({h["geo"] for h in a["H"]}) < 9: continue
    T = a["T"]
    if found(A, ev, uid, T["pt"] * 1000., T["eta"]) is False and found(L, ev, uid, T["pt"] * 1000., T["eta"]) is True:
        sel.append(a)
print(f"legacy-only particles with >= 9 own clusters, all pure seeds failing: {len(sel)}")

MISS = collections.Counter(); MED = collections.defaultdict(list); HOLE = collections.Counter(); HED = collections.defaultdict(list)
DS = collections.Counter(); REF = []; FOREIGN = []
for a in sel:
    pix = [h for h in a["H"] if not h["strip"]]; strips = [h for h in a["H"] if h["strip"]]
    drops = [s for s in a["S"] if s["p"] == 1 and s["res"] == 1]
    if not drops: continue
    b = max(drops, key=lambda s: (s["nm"], -s["nh"])); states = b["states"]
    rmax = max(s["r"] for s in states)
    vis = [v for v in a["V"] if v["p"] == 1 and "geo" in v]
    visgeo = {v["geo"] for v in vis}
    own_layers = collections.defaultdict(list)
    for h in strips: own_layers[(geo(h["geo"])["vol"], geo(h["geo"])["lay"])].append(h)
    # own strip clusters inside the reach of the dropped branch
    for h in strips:
        r, z = surf_rz(h)
        if r > rmax + 5: continue
        g = geo(h["geo"]); lay = g["lay"]
        loc0 = float(np.dot(h["g"] - h["c"], h["ex"])); pp = plane_point(pix, h)
        d = edge(loc0, pp[1] if pp else 0., lay) if g["vol"] == 23 else None
        st = at(states, r, z)
        if any(s["type"] == 0 and s["isP"] == 1 for s in st): kind = "collected"
        elif h["geo"] not in visgeo: kind = "surface never visited"
        elif any(s["type"] == 0 and s["isP"] == 0 for s in st): kind = "visited, foreign hit taken"
        elif any(s["type"] == 2 for s in st): kind = "visited, hole flagged"
        elif any(s["type"] == 1 for s in st): kind = "visited, outlier"
        else: kind = "visited, not on the branch"
        MISS[kind] += 1
        if d is not None: MED[kind].append(d)
        if kind == "visited, foreign hit taken": FOREIGN.append((a, h, r, z))
    # holes of the dropped branch in the strips
    hs = [s for s in states if s["type"] == 2 and s["r"] > 330]
    for s in hs:
        v = at(vis, s["r"], s["z"])
        if not v: HOLE["no visit record"] += 1; continue
        v = v[0]; L_ = (v["vol"], v["lay"])
        own_here = [h for h in strips if h["geo"] == v["geo"]]
        own_L = own_layers.get(L_, [])
        if own_here: kind = "own cluster on this surface (not taken)"
        elif any(h["geo"] in visgeo for h in own_L): kind = "own cluster on a neighbour, visited"
        elif own_L: kind = "own cluster on a neighbour, never visited"
        else: kind = "no own cluster on the layer"
        HOLE[kind] += 1
        HED[kind].append(edge(v["loc0"], v["loc1"], v["lay"]))
        HED["all holes, predicted outside bounds"].append(1. if edge(v["loc0"], v["loc1"], v["lay"]) < 0 else 0.)
    # double-sided misses: two holes on one layer within 12 mm in r
    hs_sorted = sorted(hs, key=lambda s: s["r"])
    for s1, s2 in zip(hs_sorted, hs_sorted[1:]):
        if abs(s2["r"] - s1["r"]) < 12:
            v1 = at(vis, s1["r"], s1["z"]); L_ = (v1[0]["vol"], v1[0]["lay"]) if v1 else None
            own_L = own_layers.get(L_, [])
            if not own_L: DS["no own cluster on the layer"] += 1; continue
            hit_geo = {h["geo"] for h in own_L}
            vis_L = [v for v in vis if (v["vol"], v["lay"]) == L_]
            if hit_geo & {v["geo"] for v in vis_L}: DS["own clusters on a visited neighbour of that layer"] += 1
            else:
                DS["own clusters only on never-visited modules of that layer"] += 1
                # where is the own module relative to the hole modules?
                hv = v1[0]; hc = next(h for h in own_L)
                DS["   own module: |dz| to hole module > 15 mm" if abs(hc["c"][2] - hv["z"]) > 15 else "   own module: same z, other phi"] += 1
# reference: edge distance of collected own strip clusters of good seeds (sample)
n = 0
for a in attempts():
    if n > 3000: break
    if a["n"] != 5 or not a["pure"] or a["att"] != 0 or a["ntr"] == 0 or a["T"] is None: continue
    pix = [h for h in a["H"] if not h["strip"]]
    for h in a["H"]:
        if not h["strip"]: continue
        g = geo(h["geo"])
        if g["vol"] != 23: continue
        pp = plane_point(pix, h)
        if pp: REF.append(edge(float(np.dot(h["g"] - h["c"], h["ex"])), pp[1], g["lay"]))
    n += 1

def frac(v, x): v = np.array(v); return f"{100*np.mean(v < x):5.1f}%" if len(v) else "   - "
print("\nown strip clusters within the reach of the dropped branch:")
print(f"   {'status':40s} {'n':>5s}  edge < 0.5 mm   < 1 mm   < 2 mm")
for k, v in MISS.most_common():
    print(f"   {k:40s} {v:5d}        {frac(MED[k], .5)}  {frac(MED[k], 1)}  {frac(MED[k], 2)}")
print(f"   {'reference: own clusters of good seeds':40s} {len(REF):5d}        {frac(REF, .5)}  {frac(REF, 1)}  {frac(REF, 2)}")
print("\nstrip holes on the dropped branch (edge distance of the CKF prediction on that surface):")
for k, v in HOLE.most_common():
    print(f"   {k:40s} {v:5d}        {frac(HED[k], .5)}  {frac(HED[k], 1)}  {frac(HED[k], 2)}")
x = HED["all holes, predicted outside bounds"]
print(f"   prediction outside the surface bounds: {100*np.mean(x) if x else 0:.1f}% of the holes")
print("\ndouble-sided misses (2 holes on one layer):")
for k, v in DS.items(): print(f"   {k:58s} {v:5d}")

if LT:
    # legacy track of the particle: most hits matching the own clusters by position
    LTR = collections.defaultdict(list)
    for line in open(LT):
        pp = line.rstrip("\n").split(" | "); h = pp[0].split()
        hits = [(x.split()[0], np.array(list(map(float, x.split()[1:4])))) for x in pp[1:]]
        LTR[int(h[1])].append(hits)
    def match(hits, clusters, tol=0.05):
        return [any(np.abs(c["g"] - g).max() < tol for c in clusters) for t, g in hits]
    LC = collections.Counter()
    for a, h, r, z in FOREIGN:
        tr = LTR.get(a["ev"], []); own = a["H"]
        if not tr: LC["no legacy tracks in event"] += 1; continue
        best = max(tr, key=lambda hits: sum(match([x for x in hits if x[0] != "h"], own)))
        nm = sum(match([x for x in best if x[0] != "h"], own))
        if nm < 5: LC["legacy track not found by position"] += 1; continue
        # legacy hit on the surface where ACTS took a foreign hit
        onsurf = [x for x in best if x[0] != "h" and abs(math.hypot(*x[1][:2]) - math.hypot(*h["g"][:2])) < 3 and abs(x[1][2] - h["g"][2]) < 60
                  and np.dot(x[1] - h["c"], np.cross(h["ex"], h["ey"])) ** 2 < 1.]
        if not onsurf: LC["legacy: no hit on that surface"] += 1
        elif any(np.abs(x[1] - h["g"]).max() < 0.05 for x in onsurf): LC["legacy: the own hit"] += 1
        else: LC["legacy: another (foreign) hit"] += 1
        LC["matched legacy tracks: own-hit fraction > 0.9"] += sum(match([x for x in best if x[0] != "h"], own)) / max(1, len([x for x in best if x[0] != "h"])) > 0.9
    print("\nsurfaces where ACTS took a foreign hit over the own one: what the legacy track has there")
    for k, v in LC.most_common(): print(f"   {k:58s} {v:5d}")
