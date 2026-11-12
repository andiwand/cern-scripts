#!/usr/bin/env python3
"""Is the early mis-pick a close call or a bad estimate? Uses the OFF selector records (R lines).
usage: soschi2.py <on/sos.txt> <off/sos.txt>"""
import sys, collections, statistics as st
exec(open(__file__.replace("soschi2.py", "sosclean.py")).read().split("SA, TA, _ = load")[0])
SA, TA, _ = load(sys.argv[1]); SB, TB, RB = load(sys.argv[2])
EXP = {0: (2, 1.386), 1: (1, 0.455)}   # dof, median of chi2(dof): pixel 2D, strip 1D
def q(v, f): return v[int(f * (len(v) - 1))] if v else float('nan')
for ty, name in ((0, "pixel"), (1, "strip")):
    def comp(k):
        t = anyt(TA.get(k, [])) or anyt(TB.get(k, []))
        return composition(t['ms'])[0] if t else "none"
    pure = [k for k in SB if k[1] == ty and k in SA and comp(k) == "pure"]
    onlyOn = {k for k in pure if k in SA and best(TA.get(k, [])) and not best(TB.get(k, []))}
    print(f"\n==== {name}: {len(pure)} truth-pure seeds; expected median chi2 {EXP[ty][1]} (chi2 with {EXP[ty][0]} dof)")
    # true-hit chi2 on each seed surface while the track is still on the true hits (all earlier ranks 0)
    by = collections.defaultdict(list); npass = collections.defaultdict(list)
    for k in pure:
        nsp = SB[k]['nm'] if ty == 0 else SB[k]['nm'] // 2
        seen = set()
        for r in RB.get(k, []):
            i = int(r[0])
            if i == 0 or i in seen: continue
            seen.add(i)
            lbl = "SP1" if i == 1 else "SP2" if i == 2 else "last" if i == nsp - 1 else "mid"
            by[lbl].append(r[3]); npass[lbl].append(r[1])
            if r[2] > 0: break   # diverged from here on
    print("   true-hit chi2 while still on track:     median   mean   90%    | candidates inside the outlier cut: mean  frac>=2")
    for lbl in ("SP1", "SP2", "mid", "last"):
        v = sorted(by[lbl]); p = npass[lbl]
        if not v: continue
        print(f"   {lbl:5s} n={len(v):7d}            {q(v,.5):7.3f} {st.mean(v):6.2f} {q(v,.9):6.2f}   | {st.mean(p):5.2f}  {sum(x>=2 for x in p)/len(p):.3f}")
    # the outranking events themselves
    for lbl, ks in (("pure seeds selected only with forcing", onlyOn), ("pure seeds selected either way", [k for k in pure if best(TB.get(k, [])) and k in SA and best(TA.get(k, []))])):
        sc, wc, rat, cnt = [], [], [], collections.Counter()
        for k in ks:
            out = [r for r in RB.get(k, []) if r[0] > 0 and r[2] > 0]
            if not out: continue
            r = out[0]; sc.append(r[3]); wc.append(r[4]); rat.append(r[3] - r[4])
            cnt["seed chi2 < expected median"] += r[3] < EXP[ty][1]
            cnt["seed chi2 > 9 (3 sigma-ish)"] += r[3] > 9
            cnt["n"] += 1
        sc.sort(); wc.sort(); rat.sort()
        if not sc: continue
        n = cnt["n"]
        print(f"   outranked, {lbl}: n={n}")
        print(f"      true-hit chi2  median {q(sc,.5):.2f}  [10% {q(sc,.1):.2f}, 90% {q(sc,.9):.2f}];  winner chi2 median {q(wc,.5):.2f} [10% {q(wc,.1):.2f}, 90% {q(wc,.9):.2f}]")
        print(f"      chi2(true)-chi2(winner) median {q(rat,.5):.2f} [10% {q(rat,.1):.2f}, 90% {q(rat,.9):.2f}];  true hit below expected median {cnt['seed chi2 < expected median']/n:.2f}, above 9 {cnt['seed chi2 > 9 (3 sigma-ish)']/n:.2f}")

    def ptb(pt): return "<1" if pt < 1 else "1-2" if pt < 2 else "2-5" if pt < 5 else ">=5"
    def etab(e): return "<1.5" if abs(e) < 1.5 else "1.5-2.5" if abs(e) < 2.5 else ">=2.5"
    for sp in (1, 2):
        H = collections.defaultdict(lambda: [0, 0, 0, []])
        for k in pure:
            r = next((r for r in RB.get(k, []) if int(r[0]) == sp), None)
            if r is None: continue
            nsp = SB[k]['nm'] if ty == 0 else SB[k]['nm'] // 2
            for key in ("pT " + ptb(SB[k]['pt']), "eta " + etab(SB[k]['eta']), "nSP " + (str(nsp) if nsp < 7 else ">=7")):
                h = H[key]; h[0] += 1; h[1] += r[3] > 9; h[2] += r[1] >= 2; h[3].append(r[3])
        print(f"   SP{sp} true-hit chi2 by seed class:   n      median   frac>9   frac(>=2 candidates)")
        for key in sorted(H):
            h = H[key]; v = sorted(h[3])
            if h[0] < 300: continue
            print(f"      {key:12s} {h[0]:8d}   {q(v,.5):6.3f}   {h[1]/h[0]:.4f}   {h[2]/h[0]:.3f}")
