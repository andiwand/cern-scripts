#!/usr/bin/env python3
"""Lost seeds (baseline track, nav variant none): on the longest dropped pass-1 branch, what state sits on the
out-of-bounds modules (matched by surface centre r, z), and the stop reason. usage: navcmp4.py base_trace nav_trace"""
import sys, collections
HX = 48.3; HY = {2: 12.1, 4: 12.1, 6: 24.2, 8: 24.2}
def okset(fn):
    R = {}
    for line in open(fn):
        if line[0] == "A":
            f = line.split()
            if f[3] == "0" and f[4] == "5" and f[6] == "1": R[(int(f[1]), int(f[2]))] = int(f[8]) > 0
    return R
B = okset(sys.argv[1])
C = collections.Counter(); a = None
def flush(a):
    if a is None or not (B.get(a["k"]) and a["ntr"] == 0): return
    C["lost seeds"] += 1
    drops = [s for s in a["S"] if s[0] == 1]
    if not drops: C["no dropped branch"] += 1; return
    nm, nh, res, sts = max(drops, key=lambda s: (s[1], -s[2]))[1:]
    outs = {(round(v[0], 1), round(v[1], 1)) for v in a["V"]}
    on = [s for s in sts if (round(s[1], 1), round(s[2], 1)) in outs]
    C[f"stop result {res}"] += 1
    C[f"branch nMeas {'>= 9' if nm >= 9 else '< 9'}"] += 1
    if not on: C["no state on an outside module"] += 1
    for s in on:
        C["state on outside module: " + {0: "own hit" if s[3] == 1 else "foreign hit", 1: "outlier", 2: "hole", 3: "no meas expected/other"}[s[0]]] += 1
    # holes elsewhere
    C["holes on branch (sum)"] += sum(1 for s in sts if s[0] == 2)
    C["foreign hits on branch, inside modules (sum)"] += sum(1 for s in sts if s[0] == 0 and s[3] == 0 and (round(s[1],1), round(s[2],1)) not in outs)
for line in open(sys.argv[2]):
    t = line[0]
    if t == "A":
        flush(a); f = line.split()
        a = dict(k=(int(f[1]), int(f[2])), ntr=int(f[8]), V=[], S=[]) if f[3] == "0" and f[4] == "5" and f[6] == "1" else None
    elif a is None: continue
    elif t == "V":
        f = line.split()
        if len(f) < 20 or f[1] != "1" or f[15] != "23": continue
        if max(abs(float(f[18])) - HX, abs(float(f[19])) - HY.get(int(f[16]), 24.2)) > 0: a["V"].append((float(f[2]), float(f[3])))
    elif t == "S":
        pp = line.rstrip("\n").split(" | "); h = pp[0].split()
        sts = [(int(x.split()[0]), float(x.split()[1]), float(x.split()[2]), int(x.split()[4])) for x in pp[1:]]
        a["S"].append((int(h[1]), int(h[3]), int(h[4]), int(h[2]), sts))
flush(a)
for k, v in sorted(C.items()): print(f"   {k:50s} {v}")
