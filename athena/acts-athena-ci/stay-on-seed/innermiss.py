#!/usr/bin/env python3
"""Why does the inward pass miss a hit? Classify per track (G lines) against a target module:
mode 'sp0': the seed's first space point (clipped seeds), for pure pixel seeds where it is not on the track;
mode 'inner': the particle's innermost pixel cluster (P lines), for pure pixel seeds starting beyond it.
usage: innermiss.py <sos.txt> sp0|inner"""
import sys, collections
fn, mode = sys.argv[1], sys.argv[2]
P = {}; G = {}; T = {}
for l in open(fn):
    c = l[0]
    if c == 'P':
        f = l.split()
        if len(f) >= 13: P[(f[1], int(f[2]))] = (float(f[11]), f[12])
    elif c == 'G':
        a, b = l.split('|'); f = a.split(); k = (f[1], f[2], f[3])
        st = []
        for e in b.split():
            p = e.split(':'); st.append((p[0], tuple(int(x) for x in p[1].split('/')), int(p[2]) if len(p) > 2 else None, float(p[3]) if len(p) > 3 else None))
        G.setdefault(k, []).append((f[4], float(f[5]), st))
    elif c == 'T':
        a, b = l.split('|'); f = a.split(); k = (f[1], f[2], f[3])
        ms = [e.split(':') for e in b.split()]
        T.setdefault(k, []).append((f[6] == '1', ms))
C = collections.Counter(); ex = collections.defaultdict(list)
for k, tr in T.items():
    if k[1] != '0' or k not in G: continue
    for (sel, ms), (g0, r0, st) in zip(tr, G[k]):
        if not sel: continue
        u = {int(m[7]) for m in ms}
        if len(u) != 1 or min(u) < 0: continue
        uid = min(u)
        if mode == 'sp0':
            code = [m[3] for m in ms if int(m[0]) == 0][0]
            if code == 'M': C["on track"] += 1; continue
            target, rT = tuple(int(x) for x in g0.split('/')), r0
        else:
            if (k[0], uid) not in P or P[(k[0], uid)][1] == '-': continue
            rT, gt = P[(k[0], uid)]; target = tuple(int(x) for x in gt.split('/'))
            r_sp0 = min(float(m[1]) for m in ms if int(m[0]) == 0)
            if r_sp0 - rT < 15: continue
            if any(s[1] == target and s[0] == 'M' and s[2] == uid for s in st): C["on track"] += 1; continue
        same_mod = [s for s in st if s[1] == target]
        same_lay = [s for s in st if s[1][:2] == target[:2] and s[1] != target]
        inner = [s for s in st if s[3] is not None and s[3] < rT - 1]
        meas = [s for s in st if s[0] == 'M']
        if same_mod: cat = f"state on the module: {same_mod[0][0]}" + (" (other particle)" if same_mod[0][0] == 'M' else "")
        elif same_lay: cat = "layer visited, other module only: " + "".join(sorted({s[0] for s in same_lay}))
        elif inner: cat = "layer skipped, hits further in"
        elif meas and abs(min(s[3] for s in meas if s[3]) - min(float(m[1]) for m in ms if int(m[0]) == (1 if mode == 'sp0' else 0))) < 0.5:
            cat = "nothing inward of the start point"
        else: cat = "other"
        C[cat] += 1
        if len(ex[cat]) < 3: ex[cat].append((k, target, round(rT, 1), [f"{s[0]}:{'/'.join(map(str, s[1]))}" for s in st[:6]]))
n = sum(C.values())
print(f"{fn} [{mode}]: {n} pure pixel seeds with a selected track")
for c, v in C.most_common(): print(f"  {c:50s} {v:6d} {100*v/n:5.2f}%")
for c, e in ex.items():
    for x in e: print("   ex", c[:30], x)
