#!/usr/bin/env python3
"""Sum the ALL column of the ACTS finalize 'statistics' tables over several logs.
usage: statsum.py <alg> <label>=<log>[,<log>...] ...   prints one column per label, differences vs the first in %."""
import re, sys


def table(path, alg):
    """rows of '<alg> INFO statistics' (the first table after that line), last column"""
    out, on = {}, False
    for l in open(path, errors="replace"):
        l = re.sub(r"^\d\d:\d\d:\d\d ", "", l.rstrip())
        if re.match(rf"{alg}\s+INFO statistics", l):
            on, out = True, {}
            continue
        if on:
            if l.startswith("|-") or "All eta" in l:
                if out and l.startswith("|-"):
                    on = False
                continue
            m = re.match(r"\|\s*(.+?)\s*\|(.*)\|\s*$", l)
            if not m:
                on = False
                continue
            out[m.group(1)] = float(m.group(2).split("|")[-1])
    return out


alg = sys.argv[1]
cols = []
for a in sys.argv[2:]:
    lab, files = a.split("=", 1)
    s = {}
    for f in files.split(","):
        for k, v in table(f, alg).items():
            s[k] = s.get(k, 0) + v
    cols.append((lab, s))
rows = list(cols[0][1])
print(f"{alg:34s}" + "".join(f"{lab:>22s}" for lab, _ in cols))
for r in rows:
    b = cols[0][1].get(r, 0)
    line = f"{r:34s}{b:22.0f}"
    for _, s in cols[1:]:
        v = s.get(r, float("nan"))
        line += f"{v:13.0f} {100 * (v / b - 1) if b else 0:+7.2f}%"
    print(line)
