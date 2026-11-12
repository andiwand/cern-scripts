#!/usr/bin/env python3
"""Clean re-analysis of the forceTrackOnSeed diagnostic dumps (primary pass only).
usage: sosclean.py <on/sos.txt> <off/sos.txt>"""
import sys, collections
def load(fn):
    S = {}; T = collections.defaultdict(list); R = {}
    for l in open(fn):
        if l[0] == 'S':
            f = l.split(); S[(int(f[1]), int(f[2]), int(f[3]))] = dict(eta=float(f[4]), pt=float(f[5]), ntr=int(f[6]), nm=int(f[7]), uid=int(f[8]))
        elif l[0] == 'T':
            a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3])); p = f[f.index('P') + 1:]
            ms = []
            for e in b.split():
                isp, r, pt_, code, c2, tr, pos, uid = e.split(':')
                ms.append(dict(isp=int(isp), pix=pt_ == 'p', code=code, chi2=float(c2), tr=tr, uid=int(uid)))
            T[k].append(dict(sel=f[6] == '1', nm=int(f[7]), nh=int(f[8]), no=int(f[9]), ntrue=int(f[12]),
                             d0=float(p[0]), z0=float(p[1]), pt=float(p[2]), eta=float(p[3]), npix=int(p[4]), nstr=int(p[5]), ms=ms))
        elif l[0] == 'R':
            a, b = l.split('|'); f = a.split(); R[(int(f[1]), int(f[2]), int(f[3]))] = [tuple(float(x) for x in e.split(':')) for e in b.split()]
    return S, T, R
def best(tr): return max([t for t in tr if t['sel']], key=lambda t: t['nm'], default=None)
def anyt(tr): return max(tr, key=lambda t: t['nm'], default=None)
def composition(ms):
    """seed composition from the per-seed-measurement truth: majority particle, wrong-hit positions by SP"""
    uids = [m['uid'] for m in ms]
    c = collections.Counter(u for u in uids if u >= 0)
    if not c: return "no truth", None
    maj, n = c.most_common(1)[0]
    if n == len(uids): return "pure", maj
    nsp = max(m['isp'] for m in ms) + 1
    wrong = sorted({m['isp'] for m in ms if m['uid'] != maj})
    pos = set()
    for i in wrong: pos.add("front" if i == 0 else "back" if i == nsp - 1 else "middle")
    frac = n / len(uids)
    return ("majority" if frac > 0.5 else "minority") + " wrong@" + "+".join(sorted(pos)), maj
def reasons(t):
    a = abs(t['eta']); b = 0 if a < 2.0 else 1 if a < 2.6 else 2
    r = []
    if t['pt'] < [0.9, 0.4, 0.4][b]: r.append("pT")
    if abs(t['d0']) > [5, 5, 10][b]: r.append("d0")
    if abs(t['z0']) > 200: r.append("z0")
    if t['nm'] < [9, 8, 7][b]: r.append("nMeas")
    if t['npix'] < 3: r.append("nPix")
    if t['nh'] > 1: r.append("holes")
    if t['no'] > 1: r.append("outliers")
    if a > 4.0: r.append("eta")
    return "+".join(r) or "other"
SA, TA, _ = load(sys.argv[1]); SB, TB, RB = load(sys.argv[2])
TYPE = {0: "pixel", 1: "strip"}
for ty in (0, 1):
    common = [k for k in SA if k[1] == ty and k in SB]
    onlyOn = [k for k in common if best(TA.get(k, [])) and not best(TB.get(k, []))]
    onlyOff = [k for k in common if best(TB.get(k, [])) and not best(TA.get(k, []))]
    bothk = [k for k in common if best(TA.get(k, [])) and best(TB.get(k, []))]
    print(f"\n######## {TYPE[ty]} seeds: processed in both {len(common)}; selected track in both {len(bothk)}, only ON {len(onlyOn)}, only OFF {len(onlyOff)}")
    # seed composition, from any track of the seed in ON (seed measurement truth is independent of the track)
    for lbl, ks, T in (("all processed (with a candidate in ON)", [k for k in common if TA.get(k)], TA), ("selected in both", bothk, TA),
                       ("selected only ON", onlyOn, TA), ("selected only OFF", onlyOff, TB)):
        c = collections.Counter(composition(anyt(T[k])['ms'])[0] for k in ks if T.get(k))
        n = sum(c.values())
        print(f"  seed composition, {lbl} (n={n}): " + ", ".join(f"{x} {v/n:.3f}" for x, v in c.most_common(8)))
    # what OFF did for seeds selected only with forcing
    c = collections.Counter(); r = collections.Counter(); rk = collections.Counter()
    for k in onlyOn:
        t = anyt(TB.get(k, []))
        comp = composition(anyt(TA[k])['ms'])[0].split()[0]
        c[(comp, "no OFF candidate" if not t else "OFF candidate fails: " + reasons(t))] += 1
        recs = [x for x in RB.get(k, []) if x[0] > 0]
        out = [x for x in recs if x[2] > 0]
        rk[(comp, "seed hit outranked by another hit" if out else "seed hit best everywhere it was offered")] += 1
    print("  seeds selected only with forcing: what happens without forcing (by seed composition)")
    for (comp, x), n in sorted(c.items(), key=lambda z: -z[1])[:14]: print(f"     {n:6d}  [{comp}] {x}")
    for (comp, x), n in sorted(rk.items(), key=lambda z: -z[1]): print(f"     {n:6d}  [{comp}] {x}")
