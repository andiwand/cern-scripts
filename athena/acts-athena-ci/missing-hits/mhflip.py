#!/usr/bin/env python3
"""Where the seed hit is outranked: by seed SP index, coordinate of the true hit's miss, |eta| and seed length.
usage: mhflip.py name=off/sos.txt ..."""
import sys, math, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from mhlib import load, q, pure_uid
for a in sys.argv[1:]:
    name, fn = a.split('=', 1)
    D = load(fn, "QRVS")
    byj = collections.Counter(); nj = collections.Counter(); coord = collections.Counter(); first = collections.Counter()
    chi = collections.defaultdict(list); npass = collections.defaultdict(list); nseeds = 0; nlen = collections.Counter(); flen = collections.Counter()
    for k, recs in D['R'].items():
        if k[1] != '0' or pure_uid(D['Q'], k) is None: continue
        u = pure_uid(D['Q'], k); V = D['V'].get((k[0], str(u)))
        if V is None or math.hypot(V[0], V[1]) > 2: continue
        nseeds += 1; L = min(len(D['Q'][k][2]), 9); nlen[L] += 1
        f = None
        for x in recs:
            if x['j'] == 0: continue
            nj[min(x['j'], 6)] += 1
            if x['rank'] != 0:
                byj[min(x['j'], 6)] += 1
                if f is None: f = x
        if f:
            first[min(f['j'], 6)] += 1; flen[L] += 1
            s0 = abs(f['r0']) / math.sqrt(max(f['P00'] + f['V00'], 1e-12)); s1 = abs(f['r1']) / math.sqrt(max(f['P11'] + f['V11'], 1e-12)) if f['dim'] == 2 else 0
            coord['loc0' if s0 >= s1 else 'loc1'] += 1
            chi[min(f['j'], 6)].append(f['chi2']); npass[min(f['j'], 6)].append(f['nPass'])
    nf = sum(first.values())
    print(f"\n{name}: {nseeds} pure prompt pixel seeds, {nf} with the seed hit outranked somewhere ({nf/nseeds:.2%})")
    print("  first outranked at seed SP j:   " + "  ".join(f"j={j}{'+' if j == 6 else ''}: {first[j]} ({first[j]/max(nj[j],1):.2%} of records, true chi2 med {q(chi[j], .5):.1f}, nPass med {q(npass[j], .5)})" for j in sorted(first)))
    print(f"  dominant coordinate of the true-hit miss: " + ", ".join(f"{c} {n} ({n/nf:.0%})" for c, n in coord.items()))
    print("  by seed length: " + "  ".join(f"{L}{'+' if L == 9 else ''}: {flen[L]/nlen[L]:.2%}" for L in sorted(nlen) if nlen[L] > 500))
