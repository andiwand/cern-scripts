#!/usr/bin/env python3
"""Composition of the 4-SP GBTS seeds at |eta| < 0.6 (unsplit seed dump). usage: fakes4.py <dir with gbtssplit.txt>"""
import sys, collections, os
L = lambda r: int((r - 20) // 50) if r < 330 else 9   # pixel barrel layer code from radius
C = collections.Counter(); PAT = collections.Counter(); LAY = collections.Counter(); PT = collections.Counter(); DST = collections.Counter()
CUR = collections.defaultdict(list)
for line in open(os.path.join(sys.argv[1], "gbtssplit.txt")):
    p = line.rstrip("\n").split(" | "); h = p[0].split()
    dst = int(p[-1].split()[1]) if p[-1].startswith("D ") else -1
    sps = p[1:-1] if p[-1].startswith("D ") else p[1:]
    n = int(h[3]); eta = float(h[4]); inv = list(map(float, h[5:8]))
    if abs(eta) >= 0.6 or n not in (4, 5): continue
    tr = []; rs = []
    for s in sps:
        f = s.split(); rs.append(float(f[0])); nc = int(f[3])
        tr.append({(int(f[4 + 3 * k]), float(f[5 + 3 * k])) for k in range(min(nc, 2))})
    cnt = collections.Counter(u for t in tr for u, _ in t)
    if not cnt: cls = "no truth"; maj = None
    else:
        maj, k = cnt.most_common(1)[0]
        cls = "pure" if k == n else "1 wrong" if k == n - 1 else "fake"
    C[(n, cls)] += 1
    lay = "".join(str(L(r)) for r in rs)
    if n == 4:
        LAY[(cls, lay)] += 1
        if cls == "fake":
            # particle pattern: letters by first-seen particle of the first contributor
            ids = {}; pat = ""
            for t in tr:
                u = min(t)[0] if t else None
                if u is None: pat += "-"; continue
                ids.setdefault(u, "ABCD"[len(ids)]); pat += ids[u]
            PAT[pat] += 1
        ptm = next((pt for t in tr for u, pt in t if u == maj), 0)
        PT[(cls, "<0.5" if ptm < 500 else "0.5-0.9" if ptm < 900 else "0.9-1.5" if ptm < 1500 else ">1.5")] += 1
        DST[(cls, dst)] += 1
        CUR[cls].append(max(abs(inv[1]-inv[0]), abs(inv[2]-inv[0]), abs(inv[2]-inv[1])))
for n in (4, 5):
    tot = sum(v for (a, _), v in C.items() if a == n)
    print(f"{n}-SP: {tot}  " + "  ".join(f"{c} {100*C[(n, c)]/tot:.1f}%" for c in ("pure", "1 wrong", "fake", "no truth")))
print("4-SP layer patterns (pixel barrel layer index per SP):")
for cls in ("pure", "fake"):
    tot = sum(v for (c, _), v in LAY.items() if c == cls)
    print(f"  {cls:5s}: " + ", ".join(f"{l} {100*v/tot:.0f}%" for (c, l), v in sorted(LAY.items(), key=lambda x: -x[1]) if c == cls and v / tot > 0.03))
tot = sum(PAT.values()); print("4-SP fake particle patterns (inner to outer, letter = particle): " + ", ".join(f"{p} {100*v/tot:.0f}%" for p, v in PAT.most_common(8)))
print("4-SP majority-particle pT [GeV]:")
for cls in ("pure", "fake"):
    tot = sum(v for (c, _), v in PT.items() if c == cls)
    print(f"  {cls:5s}: " + ", ".join(f"{b} {100*PT[(cls, b)]/tot:.0f}%" for b in ("<0.5", "0.5-0.9", "0.9-1.5", ">1.5")))
print("4-SP CKF destiny (1 succeed, 2 duplicate, 3 failure):")
for cls in ("pure", "fake"):
    tot = sum(v for (c, _), v in DST.items() if c == cls)
    print(f"  {cls:5s}: " + ", ".join(f"{d} {100*DST[(cls, d)]/tot:.0f}%" for d in (1, 2, 3)))
import statistics as st
print("4-SP max sub-triplet 1/(2R) difference, median [1/m]: " + ", ".join(f"{c} {1000*st.median(v):.4f}" for c, v in CUR.items() if v))
