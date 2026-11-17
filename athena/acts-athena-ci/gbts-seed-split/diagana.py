#!/usr/bin/env python3
"""GBTS split diagnostics: dump of the unsplit seeds (GbtsSplitDiagAlg, split off) + paired efficiency.
usage: diagana.py <off-diag dir> <on-diag dir>   (both with splitsum_pu.pkl from splitsum.py --pu)"""
import sys, collections, pickle, os
TOL = 0.7e-5
off, on = sys.argv[1:3]
def ptb(pt):
    for lo, hi in [(0, 1), (1, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 1e9)]:
        if pt / 1000 < hi: return f"{lo}-{hi if hi < 1e8 else 'inf'}"
seeds = []   # (ev, n, eta, flagged, diffs, uids per SP, majority uid, (pt, eta) of majority, r per SP)
for line in open(os.path.join(off, "gbtssplit.txt")):
    parts = line.rstrip("\n").split(" | "); h = parts[0].split()
    dst = int(parts[-1].split()[1]) if parts[-1].startswith("D ") else -1
    if parts[-1].startswith("D "): parts = parts[:-1]
    ev, n, eta = int(h[1]), int(h[3]), float(h[4]); inv = list(map(float, h[5:8]))
    sps = []
    for p in parts[1:]:
        f = p.split(); r = float(f[0]); nc = int(f[3])
        u = (int(f[4]), float(f[5]), float(f[6])) if nc > 0 else None
        sps.append((r, u))
    if abs(eta) >= 0.6 or n not in (4, 5): continue
    diffs = (abs(inv[1] - inv[0]), abs(inv[2] - inv[0]), abs(inv[2] - inv[1]))
    flagged = max(diffs) >= TOL
    cnt = collections.Counter(u[0] for _, u in sps if u)
    maj = cnt.most_common(1)[0][0] if cnt else None
    mk = next((u for _, u in sps if u and u[0] == maj), None)
    wrong = [k for k, (_, u) in enumerate(sps) if not u or u[0] != maj]
    seeds.append(dict(dst=dst, ev=ev, n=n, flagged=flagged, maxdiff=max(diffs), maj=maj, mk=mk, wrong=wrong, r=[r for r, _ in sps]))
print(f"seeds |eta|<0.6 with 4-5 SPs (split off): {len(seeds)}")
def cls(s):
    if s["maj"] is None: return "no truth"
    if not s["wrong"]: return "pure"
    if len(s["wrong"]) == 1:
        k = s["wrong"][0]; n = s["n"]
        return f"1 wrong @{k}" + (" (dropped by a child)" if k in (0, n // 2) else " (kept by both children)")
    return "2+ wrong"
for n in (4, 5):
    S = [s for s in seeds if s["n"] == n]
    print(f"== {n}-SP seeds: {len(S)}, flagged {sum(s['flagged'] for s in S)} ({100*sum(s['flagged'] for s in S)/max(1,len(S)):.1f}%)")
    C = collections.Counter((cls(s), s["flagged"]) for s in S)
    for c in sorted({k[0] for k in C}):
        a, b = C[(c, False)], C[(c, True)]
        print(f"   {c:40s} unflagged {a:7d}  flagged {b:7d}  flag rate {100*b/max(1,a+b):5.1f}%  share of flagged {100*b/max(1,sum(s['flagged'] for s in S)):5.1f}%")
    print("   flag rate of pure seeds by particle pT [GeV]: " + "  ".join(
        f"{p}: {100*sum(1 for s in S if cls(s)=='pure' and ptb(s['mk'][1])==p and s['flagged'])/max(1,sum(1 for s in S if cls(s)=='pure' and ptb(s['mk'][1])==p)):.1f}% ({sum(1 for s in S if cls(s)=='pure' and ptb(s['mk'][1])==p)})"
        for p in ["0-1", "1-1.5", "1.5-2", "2-3", "3-5", "5-inf"]))
# paired efficiency
_, TA = pickle.load(open(os.path.join(on, "splitsum_pu.pkl"), "rb"))
_, TB = pickle.load(open(os.path.join(off, "splitsum_pu.pkl"), "rb"))
byp = collections.defaultdict(list)
for s in seeds:
    if s["mk"]: byp[(s["ev"], s["maj"])].append(s)
def seedsof(key, v):
    ev, uid, pt, eta = key
    return [s for s in byp.get((ev, uid), []) if abs(s["mk"][1] - v[2]) < 1.0]
groups = {"lost when split off": [], "gained when split off": [], "found in both": [], "found in neither": []}
for k, va in TA.items():
    if va[1] not in ("0.0-0.3", "0.3-0.6") or k not in TB: continue
    a, b = bool(va[3]), bool(TB[k][3])
    g = "found in both" if a and b else "lost when split off" if a else "gained when split off" if b else "found in neither"
    groups[g].append((k, va))
print("== particles |eta|<0.6, pT>1 GeV: their 4-5 SP seeds in the unsplit seed collection")
for g, L in groups.items():
    C = collections.Counter()
    for k, v in L:
        ss = seedsof(k, v)
        if not ss: C["no 4-5 SP seed as majority"] += 1; continue
        best = max(ss, key=lambda s: (not s["wrong"], -s["flagged"]))
        C["has a 4-5 SP seed"] += 1
        C["  all its seeds flagged"] += all(s["flagged"] for s in ss)
        C["  best seed pure"] += not best["wrong"]
        C["  best seed pure and flagged"] += (not best["wrong"]) and best["flagged"]
        C["  best seed 1 wrong, dropped by a child"] += len(best["wrong"]) == 1 and best["wrong"][0] in (0, best["n"] // 2)
        C["  best seed 1 wrong, kept by both"] += len(best["wrong"]) == 1 and best["wrong"][0] not in (0, best["n"] // 2)
        C["  best seed 2+ wrong / no truth"] += len(best["wrong"]) > 1
        C[f"  pT {ptb(v[2])}"] += 1
    print(f"-- {g}: {len(L)}")
    for c in sorted(C, key=lambda x: (x.startswith("  pT"), x)): print(f"   {c:42s} {C[c]:7d}  ({100*C[c]/max(1,len(L)):5.1f}%)")
