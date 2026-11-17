#!/usr/bin/env python3
"""Seed purity by size at |eta| < 0.6 from a GbtsSplitDiagAlg dump (any pixel seeder), plus for 4-SP seeds the
layer-skip share and how often a pure layer-skipping 4-SP seed is a particle's only pure seed.
usage: seedpurity.py <gbtssplit.txt>   (pure: every SP has the majority particle among its first two contributors)"""
import sys, collections
L = lambda r: int((r - 20) // 50)        # pixel barrel layers -> 0 1 2 4 5
C = collections.Counter(); by = collections.defaultdict(list); NT = collections.Counter()
for line in open(sys.argv[1]):
    p = line.rstrip("\n").split(" | "); h = p[0].split()
    dst = int(p[-1].split()[1]) if p[-1].startswith("D ") else -1
    sps = p[1:-1] if p[-1].startswith("D ") else p[1:]
    n = int(h[3]); eta = float(h[4])
    if abs(eta) >= 0.6: continue
    tr = []; rs = []; pts = {}
    for s in sps:
        f = s.split(); rs.append(float(f[0])); nc = int(f[3])
        tr.append({int(f[4 + 3 * k]) for k in range(min(nc, 2))})
        for k in range(min(nc, 2)): pts[int(f[4 + 3 * k])] = float(f[5 + 3 * k])
    cnt = collections.Counter(u for t in tr for u in t)
    u, k = cnt.most_common(1)[0] if cnt else (None, 0)
    pure = k == n
    C[(n, "all")] += 1; C[(n, pure)] += 1; C[(n, pure, dst)] += 1
    lay = [L(r) for r in rs]
    skip = any(b - a > 1 and not (a == 2 and b == 4) for a, b in zip(lay, lay[1:]))
    if n == 4:
        C[(4, pure, "skip")] += skip
        if not pure: NT["fake with a truth-less SP"] += any(not t for t in tr); NT["fake"] += 1
    if pure: by[(int(h[1]), u)].append((n, skip, dst, pts[u]))
for n in sorted({k[0] for k in C}):
    t = C[(n, "all")]; pu = C[(n, True)]; f = C[(n, False)]
    s = f"{n}-SP {t:7d}: pure {100*pu/t:5.1f}%  not pure {100*f/t:5.1f}%   CKF success (destiny 1): pure {100*C[(n, True, 1)]/max(1,pu):.0f}%, not pure {100*C[(n, False, 1)]/max(1,f):.0f}%"
    if n == 4: s += f"   layer-skipping: pure {100*C[(4, True, 'skip')]/max(1,pu):.0f}%, not pure {100*C[(4, False, 'skip')]/max(1,f):.0f}%"
    print(s)
tot = sum(C[(n, "all")] for n in {k[0] for k in C}); pur = sum(C[(n, True)] for n in {k[0] for k in C})
print(f"all {tot}: pure {100*pur/tot:.1f}%  not pure {100*(tot-pur)/tot:.1f}%")
if NT["fake"]: print(f"4-SP not pure with an SP without truth: {100*NT['fake with a truth-less SP']/NT['fake']:.0f}%")
c = collections.Counter()
for k, ss in by.items():
    if any(n == 4 and s for n, s, _, _ in ss) and ss[0][3] >= 1000:
        only = all(n == 4 and s for n, s, _, _ in ss)
        c["particles pT > 1 GeV with a pure layer-skipping 4-SP seed"] += 1
        c["  ... as their only pure seed"] += only
        c["  ... only pure seed, which found a track"] += only and any(d == 1 for _, _, d, _ in ss)
for k, v in c.items(): print(f"{k:60s} {v}")
