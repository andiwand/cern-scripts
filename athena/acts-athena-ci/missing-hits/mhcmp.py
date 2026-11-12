#!/usr/bin/env python3
"""Compare estimation variants on per-seed dumps (forcing off): SP1 loc1 miss, seed hit outranked at SP1 / at any seed SP,
and the estimate's theta vs truth, for pure pixel seeds of prompt particles, by truth |eta|.
usage: mhcmp.py name=off/sos.txt ... [--json out.json]"""
import sys, math, json, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from mhlib import load, width, q, pure_uid
args = [a for a in sys.argv[1:] if not a.startswith('--')]
jout = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
if jout in args: args.remove(jout)
th = lambda eta: 2 * math.atan(math.exp(-eta))
BINS = ((0, 1), (1, 1.5), (1.5, 2.5), (2.5, 4.1))
OUT = {}
for a in args:
    name, fn = a.split('=', 1)
    D = load(fn, "QRVS")
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for k, recs in D['R'].items():
        if k[1] != '0' or k not in D['S']: continue
        u = pure_uid(D['Q'], k)
        if u is None: continue
        V = D['V'].get((k[0], str(u)))
        if V is None or math.hypot(V[0], V[1]) > 2: continue
        e = abs(V[4]); b = next((f"{lo}-{hi}" for lo, hi in BINS if lo <= e < hi), None)
        if b is None: continue
        r1 = next((x for x in recs if x['j'] == 1), None)
        A = acc[b]
        if r1 and r1['dim'] == 2:
            A['miss'].append(abs(r1['r1']) * 1e3); A['flip1'].append(r1['rank'] != 0)
        A['flipany'].append(any(x['rank'] != 0 for x in recs if x['j'] > 0))
        A['dth'].append((th(D['S'][k][0]) - th(V[4])) * 1e3)
    OUT[name] = {}
    print(f"\n{name}")
    print("  |eta|     seeds   |r1| med   |r1|>200   outranked SP1   outranked any SP   theta err core [mrad]")
    tot = collections.defaultdict(list)
    for b in [f"{lo}-{hi}" for lo, hi in BINS] + ["all"]:
        A = acc[b] if b != "all" else tot
        if b != "all":
            for kk, v in acc[b].items(): tot[kk] += v
        n = len(A['flipany'])
        if not n: continue
        row = dict(n=n, med=q(A['miss'], .5), tail=sum(x > 200 for x in A['miss']) / len(A['miss']),
                   flip1=sum(A['flip1']) / len(A['flip1']), flipany=sum(A['flipany']) / n, dth=width(A['dth'])[0])
        OUT[name][b] = row
        print(f"  {b:8s} {n:7d}   {row['med']:7.1f}   {row['tail']:7.1%}      {row['flip1']:6.2%}          {row['flipany']:6.2%}            {row['dth']:5.2f}")
if jout: json.dump(OUT, open(jout, 'w'), indent=1)
