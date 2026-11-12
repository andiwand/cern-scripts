#!/usr/bin/env python3
"""phi error of the local triplet vs FML by pT x SP0-SP2 lever and barrel/endcap; usage: soslocpt.py <ref off> <first3>"""
import sys, math
exec(open(__file__.replace("soslocpt.py", "sosloc.py")).read().split("ref = load(sys.argv[1])")[0])
ref = load(sys.argv[1]); v = load(sys.argv[2])
keys = [k for k in ref['F'] if k[1] == 0 and ref['comp'].get(k) and k in ref['eta'] and k in v['E'] and k in ref['E']]
def pt(k): f = ref['F'][k]; return abs(math.sin(f[3]) / f[4])
def s02(k): return (ref['rad'][k][2] - ref['rad'][k][0]) * math.cosh(ref['eta'][k])
def dphi(e, f): return ((e[2] - f[2] + math.pi) % (2 * math.pi) - math.pi) * 1e3
for reg, sel in (("|eta|<1", lambda k: abs(ref['eta'][k]) < 1), ("|eta|>=2", lambda k: abs(ref['eta'][k]) >= 2)):
    print(f"\n{reg}: phi core width [mrad]  first3 / FML   (rows lever SP0-SP2, cols pT)")
    pts = [(0, 1), (1, 2), (2, 5), (5, 1e9)]; levs = [(0, 60), (60, 120), (120, 1e9)]
    print(" " * 12 + "".join(f"{'pT %g-%g' % (a, b if b < 1e8 else 99):>18s}" for a, b in pts))
    for la, lb in levs:
        row = f"{la:4.0f}-{lb if lb < 1e8 else 'inf':>5}  "
        for a, b in pts:
            ks = [k for k in keys if sel(k) and a <= pt(k) < b and la <= s02(k) < lb]
            if len(ks) < 100: row += f"{'-':>18s}"; continue
            w1 = width([dphi(v['E'][k], ref['F'][k]) for k in ks]); w0 = width([dphi(ref['E'][k], ref['F'][k]) for k in ks])
            row += f"{w1:9.2f} /{w0:5.2f} {len(ks)//1000:2d}k"
        print(row)
