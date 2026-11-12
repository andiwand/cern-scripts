#!/usr/bin/env python3
"""Where do GBTS seeds carry wrong space points (front / middle / back, run length) vs |eta|.
SP truth from the T lines of the per-seed dump (seed measurements are listed whether or not on the track).
A SP is right if all its clusters belong to the seed's majority particle (majority over SPs).
usage: gbtswrong.py <on/sos.txt> <off/sos.txt> <out.json>"""
import sys, json, collections
def load(fn):
    seeds = {}; sel = set()
    for l in open(fn):
        if l[0] == 'S':
            f = l.split(); k = (int(f[1]), int(f[2]), int(f[3]))
            seeds.setdefault(k, {})['eta'] = float(f[4])
        elif l[0] == 'T':
            a, b = l.split('|'); f = a.split(); k = (int(f[1]), int(f[2]), int(f[3]))
            if f[6] == '1': sel.add(k)
            d = seeds.setdefault(k, {})
            if 'sp' in d: continue
            sp = collections.defaultdict(set)
            for e in b.split():
                p = e.split(':')
                if int(p[0]) >= 0: sp[int(p[0])].add(int(p[7]))
            d['sp'] = [sp[i] for i in sorted(sp)]
    return seeds, sel
def classify(sps):
    lab = [next(iter(s)) if len(s) == 1 else -2 for s in sps]
    c = collections.Counter(x for x in lab if x >= 0)
    if not c: return None
    maj = c.most_common(1)[0][0]
    w = [x != maj for x in lab]; n = len(w)
    notruth = sum(1 for x, ww in zip(lab, w) if ww and x == -1)
    mixed = sum(1 for x in lab if x == -2)
    runs = []; i = 0
    while i < n:
        if w[i]:
            j = i
            while j < n and w[j]: j += 1
            runs.append((i, j - 1)); i = j
        else: i += 1
    if 2 * c[maj] <= n: return dict(n=n, pos="no majority", run=0, nwrong=sum(w), notruth=notruth, mixed=mixed)
    if not runs: return dict(n=n, pos="pure", run=0, nwrong=0, notruth=0, mixed=0)
    if len(runs) > 1: pos = "several places"
    else:
        a, b = runs[0]
        pos = "front" if a == 0 and b < n - 1 else "back" if b == n - 1 and a > 0 else "middle" if a > 0 else "all"
    return dict(n=n, pos=pos, run=max(b - a + 1 for a, b in runs), nwrong=sum(w), notruth=notruth, mixed=mixed)
SA, selA = load(sys.argv[1]); SB, selB = load(sys.argv[2])
EDGES = [i * 0.25 for i in range(17)]
out = {}
for ty, name in ((0, "pixel"), (1, "strip")):
    H = collections.defaultdict(lambda: collections.Counter())
    tot = collections.Counter(); onlyon = collections.Counter(); onlyoff = collections.Counter(); runsBy = collections.Counter()
    nwr = collections.Counter(); ntruthless = 0; nwrongsp = 0; nmixed = 0
    for k, d in SA.items():
        if k[1] != ty or 'sp' not in d or 'eta' not in d: continue
        c = classify(d['sp'])
        if c is None: continue
        ae = abs(d['eta'])
        if ae >= 4: continue
        b = int(ae / 0.25)
        runlbl = "1" if c['run'] == 1 else "2" if c['run'] == 2 else "3" if c['run'] == 3 else ">=4"
        H[b]["all"] += 1
        if c['pos'] == "no majority": H[b]["pos:no majority"] += 1
        elif c['pos'] != "pure":
            H[b]["pos:" + c['pos']] += 1; H[b]["run:" + runlbl] += 1
            ntruthless += c['notruth']; nwrongsp += c['nwrong']; nmixed += c['mixed']
            runsBy[(c['pos'], runlbl)] += 1
        tot[c['pos']] += 1
        if k in SB:
            if k in selA and k not in selB: onlyon[c['pos']] += 1
            if k in selB and k not in selA: onlyoff[c['pos']] += 1
    N = sum(tot.values())
    print(f"\n### {name}: {N} seeds with truth")
    for p, v in tot.most_common():
        print(f"  {p:15s} {v:8d} {100*v/N:6.2f}%   selected only with forcing {onlyon[p]:5d}   only without {onlyoff[p]:5d}")
    print(f"  wrong SPs: {nwrongsp}, no truth {ntruthless}, clusters of two particles {nmixed}, another particle {nwrongsp-ntruthless-nmixed}")
    print("  run length by position:")
    for p in ("front", "middle", "back", "several places", "all"):
        print(f"    {p:15s} " + "  ".join(f"run {r}: {runsBy[(p, r)]:6d}" for r in ("1", "2", "3", ">=4")))
    out[name] = dict(edges=EDGES, bins={str(b): dict(H[b]) for b in sorted(H)},
                     totals=dict(tot), onlyOn=dict(onlyon), onlyOff=dict(onlyoff),
                     runByPos={f"{p}|{r}": v for (p, r), v in runsBy.items()}, wrongSP=dict(total=nwrongsp, noTruth=ntruthless, mixed=nmixed))
json.dump(out, open(sys.argv[3], "w"), indent=1)
