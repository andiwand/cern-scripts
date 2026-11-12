#!/usr/bin/env python3
"""How does GBTS get the hit right where the CKF does not? For pure prompt pixel seeds whose own hit is outranked
(forcing off, first outranked seed SP j >= 1):
  1. who won: same particle (another cluster of it), another particle, no truth
  2. look-ahead: residual of the true hit and of the winner to a helix through the other seed SPs, with only the SPs
     before j (what the CKF had) and with all others (what GBTS had)
  3. duplicates: is the winner in another seed; does another seed of the same particle exist; does one carry the winner
  4. outcome: does this seed / any seed give a selected track of the particle, forced and unforced
usage: mhgbts.py <off/sos.txt> <on/sos.txt>"""
import sys, math, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from mhlib import q
def pure_uid(Qd, k):
    if k not in Qd: return None
    us = {u for sp in Qd[k] for u in sp}
    return next(iter(us)) if len(us) == 1 and next(iter(us)) >= 0 else None

def loadg(fn, want_r=True):
    Q, I, X, V, R, K = {}, {}, {}, {}, {}, collections.defaultdict(list)
    for l in open(fn):
        c = l[0]
        if l[1:2] != ' ' or c not in "QIXVRK": continue
        if c == 'V':
            f = l.split(); V[(f[1], f[2])] = tuple(float(x) for x in f[3:10]); continue
        if c == 'K':
            f = l.split(); K[(f[1], f[2], f[3])].append((int(f[4]), int(f[5]))); continue
        a, b = l.split('|', 1); f = a.split(); k = (f[1], f[2], f[3])
        if c == 'Q': Q[k] = [[int(u) for u in sp.split(',')] for sp in b.split()]
        elif c == 'I': I[k] = [tuple(sp.split(',')) for sp in b.split()]
        elif c == 'X': X[k] = [tuple(float(x) for x in sp.split(',')) for sp in b.split()]
        elif c == 'R' and want_r and f[2] == '0':
            first = None
            for e in b.split():
                x = e.split(':')
                if int(x[0]) >= 1 and int(x[2]) != 0 and len(x) >= 21:
                    first = dict(j=int(x[0]), chi2=float(x[3]), best=float(x[4]), wtype=x[15], widx=x[16], wtruth=int(x[17]),
                                 w=(float(x[18]), float(x[19]), float(x[20])))
                    break
            R[k] = first
    return Q, I, X, V, R, K

def circle(pts):
    """algebraic (Kasa) circle fit in x-y: returns (xc, yc, R) or None"""
    n = len(pts)
    if n < 3: return None
    sx = sum(p[0] for p in pts) / n; sy = sum(p[1] for p in pts) / n
    u = [(p[0] - sx, p[1] - sy) for p in pts]
    suu = sum(a * a for a, b in u); svv = sum(b * b for a, b in u); suv = sum(a * b for a, b in u)
    suuu = sum(a ** 3 for a, b in u); svvv = sum(b ** 3 for a, b in u); suvv = sum(a * b * b for a, b in u); svuu = sum(b * a * a for a, b in u)
    det = suu * svv - suv * suv
    if abs(det) < 1e-12: return None
    rhs1 = 0.5 * (suuu + suvv); rhs2 = 0.5 * (svvv + svuu)
    uc = (rhs1 * svv - rhs2 * suv) / det; vc = (suu * rhs2 - suv * rhs1) / det
    return sx + uc, sy + vc, math.sqrt(uc * uc + vc * vc + (suu + svv) / n)

def resid(pts, p):
    """transverse residual to the circle through pts and z residual to the line z(s) through pts; extrapolation if p
    lies outside pts. With 2 points: straight line in x-y. Returns (dxy, dz) in mm, or None."""
    if len(pts) < 2: return None
    if len(pts) >= 3:
        c = circle(pts)
        if c is None or c[2] > 1e6: c = None
    else: c = None
    o = pts[0]
    if c:
        xc, yc, Rr = c
        dxy = abs(math.hypot(p[0] - xc, p[1] - yc) - Rr)
        a0 = math.atan2(o[1] - yc, o[0] - xc)
        def s(x):
            d = math.atan2(x[1] - yc, x[0] - xc) - a0
            d = (d + math.pi) % (2 * math.pi) - math.pi
            return d * Rr   # signed, so that extrapolation inwards works
    else:
        a, b = pts[0], pts[-1]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        if L == 0: return None
        dxy = abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / L
        def s(x): return ((x[0] - o[0]) * dx + (x[1] - o[1]) * dy) / L
    ss = [s(x) for x in pts]; zz = [x[2] for x in pts]
    n = len(pts); ms = sum(ss) / n; mz = sum(zz) / n
    vs = sum((x - ms) ** 2 for x in ss)
    if vs == 0: return None
    k = sum((x - ms) * (z - mz) for x, z in zip(ss, zz)) / vs
    dz = abs(p[2] - (mz + k * (s(p) - ms)))
    return dxy, dz

off = loadg(sys.argv[1]); on = loadg(sys.argv[2], want_r=False)
Q, I, X, V, R, K = off
# measurement -> seeds containing it, per event
mseeds = collections.defaultdict(set)
for k, ids in I.items():
    for sp in ids:
        for m in sp: mseeds[(k[0], m)].add(k)
def seedmaj(Qd, k):
    c = collections.Counter(u for sp in Qd[k] for u in sp); u, n = c.most_common(1)[0]
    return u if u >= 0 and n * 2 > sum(c.values()) else None
# particles found (selected track with the particle as majority) per run, before ambiguity resolution
def found(Kd):
    F = set()
    for k, lst in Kd.items():
        for sel, maj in lst:
            if sel and maj >= 0: F.add((k[0], maj))
    return F
Foff, Fon = found(K), found(on[5])
pseeds = collections.defaultdict(list)   # particle -> pixel seeds with it as majority
for k in Q:
    if k[1] != '0': continue
    u = seedmaj(Q, k)
    if u is not None: pseeds[(k[0], u)].append(k)

C = collections.Counter(); look = collections.defaultdict(list); rows = []
for k, r in R.items():
    if r is None or k not in X or k not in I: continue
    u = pure_uid(Q, k)
    if u is None: continue
    Vt = V.get((k[0], str(u)))
    if Vt is None or math.hypot(Vt[0], Vt[1]) > 2: continue
    C['outranked'] += 1
    who = "same particle" if r['wtruth'] == u else ("no truth" if r['wtruth'] < 0 else "other particle")
    C['winner: ' + who] += 1
    j = r['j']; Xs = X[k]; t = Xs[j]
    if r['wtype'] == '1':
        for lab, pts in (("past (SP0..j-1)", Xs[:j]), ("future (SPj+1..)", Xs[j + 1:]), ("all others", Xs[:j] + Xs[j + 1:])):
            rt = resid(pts, t); rw = resid(pts, r['w'])
            if rt and rw:
                look[lab].append((rt, rw))
    wm = f"{r['wtype']}:{r['widx']}"
    others = mseeds.get((k[0], wm), set()) - {k}
    same = [s for s in pseeds.get((k[0], u), []) if s != k]
    C['winner in another seed'] += bool(others)
    C['winner in another seed of the same particle'] += any(seedmaj(Q, s) == u for s in others)
    C['other seed of the same particle exists'] += bool(same)
    K_this_off = any(sel and maj == u for sel, maj in K.get(k, []))
    C['this seed: selected track of the particle, unforced'] += K_this_off
    C['this seed: selected track of the particle, forced'] += any(sel and maj == u for sel, maj in on[5].get(k, []))
    C['particle found, unforced'] += (k[0], u) in Foff
    C['particle found, forced'] += (k[0], u) in Fon
    rows.append((k, u, j, who))
n = C['outranked']
print(f"pure prompt pixel seeds with the seed hit outranked (forcing off): {n}")
for key in ["winner: same particle", "winner: other particle", "winner: no truth", "winner in another seed",
            "winner in another seed of the same particle", "other seed of the same particle exists",
            "this seed: selected track of the particle, unforced", "this seed: selected track of the particle, forced",
            "particle found, unforced", "particle found, forced"]:
    print(f"  {key:52s} {C[key]:6d}  {C[key] / n:6.1%}")
print("\nlook-ahead (pixel winners): does a helix through the other seed SPs prefer the true hit?")
print("  fit points             n     true closer (xy+z)   true |dxy| / winner |dxy| med [um]   true |dz| / winner |dz| med [um]")
for lab, v in look.items():
    closer = sum((a[0] ** 2 + a[1] ** 2) < (b[0] ** 2 + b[1] ** 2) for a, b in v) / len(v)
    print(f"  {lab:18s} {len(v):6d}       {closer:6.1%}            {q([a[0] for a, b in v], .5) * 1e3:7.1f} / {q([b[0] for a, b in v], .5) * 1e3:7.1f}"
          f"                  {q([a[1] for a, b in v], .5) * 1e3:7.1f} / {q([b[1] for a, b in v], .5) * 1e3:7.1f}")
# lost particles: found forced, not unforced, and the outranked seeds behind them
lost = {(k[0], u) for k, u, j, w in rows if (k[0], u) in Fon and (k[0], u) not in Foff}
print(f"\nparticles of these seeds found forced but not unforced: {len(lost)} of {len({(k[0], u) for k, u, j, w in rows})}")

# split by outcome: lost (found forced, not unforced) vs the rest, winner type and look-ahead preference
print("\nby outcome of the particle:")
byo = collections.defaultdict(collections.Counter); la = collections.defaultdict(list)
for k, u, j, who in rows:
    o = "lost unforced" if (k[0], u) in lost else ("found both" if (k[0], u) in Foff else "found neither / other")
    byo[o][who] += 1; byo[o]['n'] += 1; byo[o][f"j={min(j, 4)}{'+' if j >= 4 else ''}"] += 1
    r = R[k]
    if r['wtype'] == '1':
        Xs = X[k]; pts = Xs[:j] + Xs[j + 1:]; rt = resid(pts, Xs[j]); rw = resid(pts, r['w'])
        if rt and rw: la[o].append((rt[0] ** 2 + rt[1] ** 2) < (rw[0] ** 2 + rw[1] ** 2))
for o, c in byo.items():
    n = c['n']
    print(f"  {o:22s} n={n:5d}  winner same/other/no truth {c['same particle']/n:5.1%} / {c['other particle']/n:5.1%} / {c['no truth']/n:5.1%}"
          f"   first outranked at j=1/2/3/4+ {c['j=1']/n:5.1%} / {c['j=2']/n:5.1%} / {c['j=3']/n:5.1%} / {c['j=4+']/n:5.1%}"
          f"   look-ahead prefers true {sum(la[o])/max(len(la[o]),1):5.1%}")
