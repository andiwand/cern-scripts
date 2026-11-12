#!/usr/bin/env python3
"""Paired seeds between two sos dumps. usage: sospair.py <A/sos.txt> <B/sos.txt>"""
import sys, collections
sys.argv_saved = sys.argv; sys.argv = sys.argv[:1]
from sosana_lib import load, best, TYPE, ptb, etab
sys.argv = sys.argv_saved
A, B = load(sys.argv[1]), load(sys.argv[2])
def summ(tr):
    if not tr: return "no candidate"
    t = max(tr, key=lambda t: (t['sel'], t['nm']))
    codes = collections.Counter(m['code'] + (m['tr'] if m['code'] in 'XY' else '') for m in t['ms'])
    return t, codes
for la, lb, (SA, TA), (SB, TB) in (("ON", "OFF", A, B), ("OFF", "ON", B, A)):
    print(f"===== truth-pure seeds with a selected track in {la} but not in {lb}")
    for ty in (0, 1):
        ks = [k for k in SA if k[1] == ty and SA[k]['uid'] >= 0 and best(TA.get(k, [])) and k in SB and not best(TB.get(k, []))]
        notproc = [k for k in SA if k[1] == ty and SA[k]['uid'] >= 0 and best(TA.get(k, [])) and k not in SB]
        cat = collections.Counter(); ex = []
        for k in ks:
            tr = TB.get(k, [])
            if not tr: cat["no CKF track (stopped/failed)"] += 1; continue
            t = max(tr, key=lambda t: t['nm']); a = best(TA[k])
            lost = [m for m in t['ms'] if m['code'] != 'M']
            c = "seed hits all kept" if not lost else "lost seed hit(s): " + ",".join(sorted({m['code'] + m['tr'] for m in lost}))
            cat[c] += 1
            if len(ex) < 6: ex.append((k, a['nm'], a['nh'], a['ntrue'], t['nm'], t['nh'], t['no'], t['ntrue'], SA[k]['pt'], SA[k]['eta']))
        print(f"  {TYPE[ty]}: {len(ks)} seeds (+{len(notproc)} not processed in {lb}, i.e. skipped as duplicate)")
        for c, n in cat.most_common(): print(f"     {n:6d}  {c}")
        for e in ex: print(f"     ex {e[0]} pt={e[8]:.2f} eta={e[9]:+.2f}  {la}: nMeas {e[1]} holes {e[2]} true {e[3]}   {lb}: nMeas {e[4]} holes {e[5]} outl {e[6]} true {e[7]}")
