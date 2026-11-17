#!/usr/bin/env python3
"""Seed destinies (TrackFindingAlg SeedDestiny) of each particle's seeds, split off vs on.
usage: diagdst.py <off-diag dir> <on-diag dir>"""
import sys, collections, pickle, os
TOL = 0.7e-5
DN = {-1: "n/a", 0: "unknown", 1: "succeed", 2: "duplicate", 3: "failure"}
def load(d, sizes):
    out = collections.defaultdict(list)
    for line in open(os.path.join(d, "gbtssplit.txt")):
        parts = line.rstrip("\n").split(" | "); h = parts[0].split()
        dst = int(parts[-1].split()[1]); parts = parts[:-1]
        ev, n, eta = int(h[1]), int(h[3]), float(h[4]); inv = list(map(float, h[5:8]))
        if abs(eta) >= 0.6 or n not in sizes: continue
        sps = []
        for p in parts[1:]:
            f = p.split(); u = (int(f[4]), float(f[5])) if int(f[3]) > 0 else None
            sps.append((float(f[0]), u))
        cnt = collections.Counter(u[0] for _, u in sps if u)
        if not cnt: continue
        maj = cnt.most_common(1)[0][0]; pt = next(u[1] for _, u in sps if u and u[0] == maj)
        pure = all(u and u[0] == maj for _, u in sps)
        flagged = n >= 4 and max(abs(inv[1]-inv[0]), abs(inv[2]-inv[0]), abs(inv[2]-inv[1])) >= TOL
        lay = "".join(str(int((r - 20) // 50)) for r, _ in sps)   # coarse layer code from radius
        out[(ev, maj)].append(dict(n=n, pt=pt, pure=pure, flagged=flagged, dst=DN[dst], lay=lay))
    return out
off, on = sys.argv[1:3]
SO = load(off, (4, 5)); SN = load(on, (3, 4, 5))
_, TA = pickle.load(open(os.path.join(on, "splitsum_pu.pkl"), "rb"))
_, TB = pickle.load(open(os.path.join(off, "splitsum_pu.pkl"), "rb"))
def seeds(S, k, v): return [s for s in S.get((k[0], k[1]), []) if abs(s["pt"] - v[2]) < 1.0]
groups = collections.defaultdict(list)
for k, va in TA.items():
    if va[1] not in ("0.0-0.3", "0.3-0.6") or k not in TB: continue
    a, b = bool(va[3]), bool(TB[k][3])
    groups["lost when split off" if a and not b else "gained when split off" if b and not a else "found in both" if a else "found in neither"].append((k, va))
for g in ("lost when split off", "gained when split off", "found in both"):
    L = groups[g]
    C = collections.Counter(); E = collections.Counter(); P = collections.Counter()
    for k, v in L:
        so = [s for s in seeds(SO, k, v) if s["pure"]]
        sn = [s for s in seeds(SN, k, v) if s["pure"]]
        C["off: " + ("+".join(sorted(f"{s['n']}{'F' if s['flagged'] else ''}:{s['dst']}" for s in so)) or "no pure seed")] += 1
        E["on: " + ("+".join(sorted(f"{s['n']}:{s['dst']}" for s in sn)) or "no pure seed")] += 1
        if g != "found in both": P[" / ".join(f"{s['lay']}:{s['dst']}" for s in sorted(so, key=lambda s: s['lay'])) + "  ->  " + " / ".join(f"{s['lay']}:{s['dst']}" for s in sorted(sn, key=lambda s: s['lay']))] += 1
    print(f"== {g}: {len(L)}   (pure seeds per particle; nF = n SPs, flagged)")
    for c, x in C.most_common(8): print(f"   {x:6d} {100*x/len(L):5.1f}%  {c}")
    for c, x in E.most_common(8): print(f"   {x:6d} {100*x/len(L):5.1f}%  {c}")
    if P:
        print("   layer codes (r bins of 50 mm) off -> on, most common:")
        for c, x in P.most_common(8): print(f"   {x:6d}  {c}")
# destiny rates of pure flagged 5-SP seeds at pT 1-1.5 vs unflagged, split off
print("== split off: destiny of pure 4-5 SP seeds, pT 1-1.5 GeV")
D = collections.Counter()
for ss in SO.values():
    for s in ss:
        if s["pure"] and 1000 <= s["pt"] < 1500: D[(s["n"], s["flagged"], s["dst"])] += 1
for n in (4, 5):
    for f in (False, True):
        tot = sum(x for (a, b, _), x in D.items() if a == n and b == f)
        print(f"   {n}-SP {'flagged  ' if f else 'unflagged'} {tot:7d}: " + "  ".join(f"{d} {100*D[(n, f, d)]/max(1,tot):5.1f}%" for d in ("succeed", "duplicate", "failure", "unknown")))
