#!/usr/bin/env python3
"""Strip barrel visits with the navigator tolerance: how many predictions lie outside the module bounds, what the CKF
does there (hit taken, own or foreign, hole, no measurement expected), and why branches stop.
usage: navcmp.py name=trace.txt ..."""
import sys, collections
HX = 48.3; HY = {2: 12.1, 4: 12.1, 6: 24.2, 8: 24.2}
for arg in sys.argv[1:]:
    name, fn = arg.split("=", 1)
    C = collections.Counter(); S = collections.Counter()
    for line in open(fn):
        if line[0] == "V":
            f = line.split()
            if len(f) < 20 or int(f[15]) != 23: continue
            lay = int(f[16]); l0, l1 = float(f[18]), float(f[19])
            out = max(abs(l0) - HX, abs(l1) - HY.get(lay, 24.2))
            k = "outside" if out > 0 else "inside"
            C[(k, "visits")] += 1
            C[(k, "candidates")] += int(f[8]) > 0
            C[(k, "pass")] += int(f[9]) > 0
            C[(k, "pass, own best")] += int(f[9]) > 0 and f[11] == "1"
            C[(k, "pass, foreign best")] += int(f[9]) > 0 and f[11] != "1"
            if k == "outside": C[("outside", f"by <1mm" if out < 1 else "by 1-3mm" if out < 3 else "by >3mm")] += 1
        elif line[0] == "S":
            pp = line.rstrip("\n").split(" | "); h = pp[0].split()
            if h[1] != "1": continue
            st = [x.split() for x in pp[1:]]
            S[("result", h[2])] += 1
            S["states"] += len(st)
            for x in st:
                S[("type", x[0])] += 1
    print(f"== {name}")
    for k in ("inside", "outside"):
        n = C[(k, "visits")]
        print(f"   {k:8s} visits {n:9d}  with candidates {C[(k,'candidates')]/max(n,1):.3f}  hit passes {C[(k,'pass')]/max(n,1):.3f}"
              f"  own best {C[(k,'pass, own best')]/max(n,1):.3f}  foreign best {C[(k,'pass, foreign best')]/max(n,1):.3f}")
    print("   outside by:", {k[1]: v for k, v in C.items() if k[0] == "outside" and k[1].startswith("by")})
    print("   pass-1 stops by result:", {k[1]: v for k, v in S.items() if isinstance(k, tuple) and k[0] == "result"},
          " state types:", {k[1]: v for k, v in S.items() if isinstance(k, tuple) and k[0] == "type"})
