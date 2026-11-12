#!/usr/bin/env python3
"""Is the start-direction error of the FirstMiddleLast estimate normal (Highland core) multiple scattering?
u = dtheta / sigma_expected, sigma_expected from Highland per seed SP layer, weighted by the chord lever arm.
usage: sosms.py <on/sos.txt> <off/sos.txt> [x/X0 per layer, default 0.02]"""
import sys, collections, statistics as st, math
src = open(__file__.replace("sosms.py", "sospull.py")).read()
exec(src.split("SA, TA, _ = load(sys.argv[1])")[0].replace('open(__file__.replace("sospull.py", "sosclean.py"))', 'open(__file__.replace("sosms.py", "sosclean.py"))'))
X = float(sys.argv[3]) if len(sys.argv) > 3 else 0.02
SA, TA, _ = load(sys.argv[1]); SB, TB, _ = load(sys.argv[2]); EA = loadE(sys.argv[1])
rad = {}
for l in open(sys.argv[1]):
    if l[0] != 'T': continue
    a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
    if k in rad or f[2] != '0': continue
    rs = {}
    for e in b.split():
        p = e.split(':'); rs[int(p[0])] = float(p[1])
    rad[k] = [rs[i] for i in sorted(rs)]
def comp(k):
    t = anyt(TA.get(k, [])) or anyt(TB.get(k, []))
    return composition(t['ms'])[0] if t else "none"
pure = [k for k in SB if k[1] == 0 and k in SA and comp(k) == "pure" and k in EA and k in rad and len(rad[k]) >= 3]
only = set(k for k in pure if best(TA.get(k, [])) and not best(TB.get(k, [])))
def sig(k):
    par = EA[k][0]; th = par[3][2]; p = abs(1 / par[4][2])   # GeV
    path = 1 / max(abs(math.sin(th)), abs(math.cos(th)))
    xx = X * path
    t0 = 0.0136 / p * math.sqrt(xx) * (1 + 0.038 * math.log(xx))
    r = rad[k]; rl = r[-1]; r0 = r[0]
    if rl - r0 <= 0: return None
    # kinks at every seed SP before the last one (incl. the start SP: material after the measurement)
    w2 = sum(((rl - rk) / (rl - r0)) ** 2 for rk in r[:-1])
    return t0 * math.sqrt(w2)
def dth(k): par = EA[k][0]; return par[3][0] - par[3][2]
for lbl, ks in (("all pure pixel seeds", pure), ("pure, found only with forcing", only)):
    u = []
    for k in ks:
        s = sig(k)
        if s: u.append(dth(k) / s)
    w, m = width(u); n = len(u)
    a = [abs(x) for x in u]
    print(f"{lbl:32s} n={n:7d}  u core width {w:.2f}  | fraction beyond 2/3/5/10 core widths: " +
          " ".join(f"{sum(x > c * w for x in a)/n:.4f}" for c in (2, 3, 5, 10)) + "   (Gaussian: 0.0455 0.0027 0.0000 0)")
# observed theta error vs expectation, binned by expectation
print("\n binned by expected sigma [mrad]: observed theta-error core [mrad]   (ratio)")
H = collections.defaultdict(list)
for k in pure:
    s = sig(k)
    if not s: continue
    b = min(int(s * 1000 / 0.25), 12)
    H[b].append((dth(k), s))
for b in sorted(H):
    v = H[b]
    if len(v) < 300: continue
    obs = width([x[0] for x in v])[0] * 1000; exp_ = st.median(x[1] for x in v) * 1000
    print(f"   exp {exp_:5.2f}  n={len(v):7d}  observed {obs:5.2f}  ratio {obs/exp_:.2f}")
