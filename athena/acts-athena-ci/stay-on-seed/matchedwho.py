#!/usr/bin/env python3
"""Which particles do matched seeds belong to? Joins Q (seeds) and P (particles) lines of one dump.
usage: matchedwho.py <sos.txt> [out.json]"""
import sys, json, collections
P = {}; Q = []
for l in open(sys.argv[1]):
    if l[0] == 'P':
        _, ev, idx, pt, eta, q, st, uid, pr, npix, nstr = l.split()
        P[(int(ev), int(idx))] = (float(pt), float(eta), float(q), int(st), int(uid), float(pr), int(npix), int(nstr))
    elif l[0] == 'Q':
        a, b = l.split('|'); f = a.split()
        lab = []
        for sp in b.split():
            u = set(int(x) for x in sp.split(',')); lab.append(next(iter(u)) if len(u) == 1 else -2)
        Q.append((int(f[1]), int(f[2]), abs(float(f[5])), lab))
def cat(p):
    if p is None: return "no particle record"
    pt, eta, q, st, uid, pr, npix, nstr = p; a = abs(eta)
    if st > 20000: return "secondary (simulation, status 2xxxx)"
    if st != 1 or q == 0: return "other primary"
    if pt < 900: return "primary pT < 0.9 GeV" if pt >= 500 else "primary pT < 0.5 GeV"
    if pr >= 300: return "primary, production radius >= 300 mm"
    if a >= 4: return "primary, |eta| >= 4"
    need = 9 if a < 2.0 else 8 if a < 2.6 else 7
    return "reconstructable" if (npix + nstr >= need and npix >= 3) else "pT > 0.9 GeV, too few clusters"
seen = set(); H = {0: collections.defaultdict(collections.Counter), 1: collections.defaultdict(collections.Counter)}
T = {0: collections.Counter(), 1: collections.Counter()}
for ev, ty, eta, lab in Q:
    if eta >= 4: continue
    c = collections.Counter(x for x in lab if x >= 0)
    if not c: continue
    maj, n = c.most_common(1)[0]
    if n < 3 or 2 * n < len(lab) or (ev, ty, maj) in seen: continue
    seen.add((ev, ty, maj))
    k = cat(P.get((ev, maj))); H[ty][int(eta / 0.25)][k] += 1; T[ty][k] += 1
for ty, name in ((0, "pixel"), (1, "strip")):
    n = sum(T[ty].values()); print(f"\n{name}: {n} matched seeds")
    for k, v in T[ty].most_common(): print(f"   {k:32s} {v:7d} {100*v/n:5.1f}%")
    print("   per |eta| bin, reconstructable / all matched: " + " ".join(f"{b*0.25:.2f}:{H[ty][b]['reconstructable']}/{sum(H[ty][b].values())}" for b in sorted(H[ty])))
if len(sys.argv) > 2:
    G = {"reconstructable": "reco", "primary pT < 0.9 GeV": "lowpt", "primary pT < 0.5 GeV": "lowpt", "secondary (simulation, status 2xxxx)": "sec"}
    def simple(v):
        o = collections.Counter()
        for k, x in v.items(): o[G.get(k, "other")] += x
        return dict(o, all=sum(v.values()))
    json.dump({n: dict(edges=[i * 0.25 for i in range(17)], bins={str(b): simple(v) for b, v in sorted(H[ty].items())})
               for ty, n in ((0, "pixel"), (1, "strip"))}, open(sys.argv[2], "w"), indent=1)
