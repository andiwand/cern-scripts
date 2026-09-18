#!/usr/bin/env python3
"""Callers of given symbols in a perf profile: for each sample containing the
symbol, the frame directly above its outermost occurrence."""
import sys, re, collections, subprocess
data = sys.argv[1]; targets = sys.argv[2:]
proc = subprocess.Popen(["perf", "script", "-i", data, "--no-inline", "-F", "ip,sym,dso"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
FRAME = re.compile(r"^\s+[0-9a-f]+\s+(.*?)\s+\((.*)\)\s*$")
def short(s):
    s = re.sub(r"\(.*", "", s).replace("Acts::Experimental::", "").replace("ActsTrk::", "")
    return s.strip()[:90]
callers = {t: collections.Counter() for t in targets}
total = {t: 0 for t in targets}
frames = []
def flush(fr):
    if not fr: return
    syms = [short(f) for f in fr]
    if not any("TrackFindingRzAlg::execute" in s for s in syms): return
    for t in targets:
        idx = [i for i, s in enumerate(syms) if t in s]
        if not idx: continue
        total[t] += 1
        i = idx[-1]
        callers[t][syms[i + 1] if i + 1 < len(syms) else "<top>"] += 1
for line in proc.stdout:
    if not line.strip(): flush(frames); frames = []; continue
    m = FRAME.match(line)
    if m: frames.append(m.group(1))
flush(frames)
for t in targets:
    print(f"\n{t}: {total[t]} samples, by caller:")
    for s, n in callers[t].most_common(8):
        print(f"  {n:6d} {100*n/max(1,total[t]):6.1f}%  {s}")
