#!/usr/bin/env python3
"""Truth classification of every input seed from the Q lines, per |eta| bin.
matched: a particle owns >= 3 and >= 50% of the SPs (a strip SP needs both clusters) and this is its first seed (seed index order, per event and seed type);
duplicate: further seeds of that particle; fake: no such particle; unlinked: no space point has truth.
Wrong SPs (position, longest run) for the matched + duplicate seeds; forcing columns from the on/off dumps (seeds with a selected track).
usage: seedclass.py <Q dump> <on sos.txt> <off sos.txt> <seedclass.json> <gbtswrong.json>"""
import sys, json, collections
def selected(fn):
    s = set()
    for l in open(fn):
        if l[0] == 'T':
            f = l.split()
            if f[6] == '1': s.add((int(f[1]), int(f[2]), int(f[3])))
    return s
EDGES = [i * 0.25 for i in range(17)]
C = {0: collections.defaultdict(collections.Counter), 1: collections.defaultdict(collections.Counter)}
W = {0: collections.defaultdict(collections.Counter), 1: collections.defaultdict(collections.Counter)}
seen = set(); comp = {}; tot = {0: collections.Counter(), 1: collections.Counter()}; runpos = {0: collections.Counter(), 1: collections.Counter()}
wrongsp = {0: collections.Counter(), 1: collections.Counter()}
for l in open(sys.argv[1]):
    if l[0] != 'Q': continue
    a, b = l.split('|'); f = a.split(); ev, ty, iseed, dup, eta = int(f[1]), int(f[2]), int(f[3]), f[4] == '1', abs(float(f[5]))
    if eta >= 4: continue
    bn = int(eta / 0.25)
    lab = []
    for sp in b.split():
        u = set(int(x) for x in sp.split(','))
        lab.append(next(iter(u)) if len(u) == 1 else -2)
    c = collections.Counter(x for x in lab if x >= 0); n = len(lab)
    maj = c.most_common(1)[0] if c else (None, 0)
    if all(x == -1 for x in lab):
        cls = "unlinked"   # every space point without truth (no truth link, as for tracks)
    elif maj[1] < 3 or maj[1] * 2 < n:
        cls = "fake"
    else:
        key = (ev, ty, maj[0]); cls = "duplicate" if key in seen else "matched"; seen.add(key)
    if cls == "fake":
        C[ty][bn]["fake no truth" if not c else "fake one particle short" if len(c) == 1 else "fake mixed"] += 1
    C[ty][bn][cls] += 1; C[ty][bn][cls + (" skipped" if dup else " processed")] += 1; C[ty][bn]["all"] += 1
    if cls in ("fake", "unlinked"): comp[(ev, ty, iseed)] = cls; continue
    w = [x != maj[0] for x in lab]
    runs = []; i = 0
    while i < n:
        if w[i]:
            j = i
            while j < n and w[j]: j += 1
            runs.append((i, j - 1)); i = j
        else: i += 1
    if not runs: p = "pure"; rl = 0
    elif len(runs) > 1: p = "several places"; rl = max(y - x + 1 for x, y in runs)
    else:
        x, y = runs[0]; rl = y - x + 1
        p = "front" if x == 0 else "back" if y == n - 1 else "middle"
    for x in lab:
        if x != maj[0]: wrongsp[ty]["no truth" if x == -1 else "two particles" if x == -2 else "other particle"] += 1
    W[ty][bn]["all"] += 1
    if p != "pure":
        W[ty][bn]["pos:" + p] += 1
        W[ty][bn]["run:" + ("1" if rl == 1 else "2" if rl == 2 else "3" if rl == 3 else ">=4")] += 1
        runpos[ty][(p, rl == 1)] += 1
    comp[(ev, ty, iseed)] = p; tot[ty][p] += 1
selA, selB = selected(sys.argv[2]), selected(sys.argv[3])
out = {}; outw = {}
for ty, name in ((0, "pixel"), (1, "strip")):
    T = collections.Counter()
    for v in C[ty].values(): T.update(v)
    print(f"\n### {name}: {T['all']} seeds; matched {T['matched']}, duplicate {T['duplicate']}, fake {T['fake']}, unlinked {T['unlinked']}")
    print(f"   fakes: no truth at all {T['fake no truth']}, one particle but < 3 or < 50% {T['fake one particle short']}, several particles {T['fake mixed']}")
    for k in ("matched", "duplicate", "fake", "unlinked"):
        print(f"   {k:10s} processed {T[k+' processed']:7d}  skipped by the duplicate detector {T[k+' skipped']:7d}")
    on = collections.Counter(); off = collections.Counter()
    for k, p in comp.items():
        if k[1] != ty: continue
        if k in selA and k not in selB: on[p] += 1
        if k in selB and k not in selA: off[p] += 1
    print(f"   fake: only-on {on['fake']} only-off {off['fake']}; unlinked: only-on {on['unlinked']} only-off {off['unlinked']}")
    nm = sum(tot[ty].values())
    print(f"   matched + duplicate {nm}: " + ", ".join(f"{p} {v} ({100*v/nm:.2f}%) only-on {on[p]} only-off {off[p]}" for p, v in tot[ty].most_common()))
    imp = nm - tot[ty]["pure"]; single = sum(v for (p, s), v in runpos[ty].items() if s)
    print(f"   impure {imp}, single wrong SP {single} ({100*single/max(imp,1):.1f}%); wrong SPs: " + ", ".join(f"{k} {v}" for k, v in wrongsp[ty].items()))
    out[name] = dict(edges=EDGES, bins={str(b): dict(v) for b, v in sorted(C[ty].items())})
    outw[name] = dict(edges=EDGES, bins={str(b): dict(v) for b, v in sorted(W[ty].items())}, totals=dict(tot[ty]), onlyOn=dict(on), onlyOff=dict(off), wrongSP=dict(wrongsp[ty]))
json.dump(out, open(sys.argv[4], "w"), indent=1); json.dump(outw, open(sys.argv[5], "w"), indent=1)
