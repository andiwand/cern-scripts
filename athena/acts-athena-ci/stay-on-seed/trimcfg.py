#!/usr/bin/env python3
"""Print the per-tool (pixel, strip) attribute list for a trimming variant, for variant_defs.sh.
usage: trimcfg.py <variant>   e.g. fit-map08 fit-res05 fml-map08 fit-zcut fit-zdw"""
import sys, json
M = json.load(open("/home/astefl/source/acts/acts-athena-ci/run/stay-on-seed/trimmaps.json"))
FIT = [{"parameterEstimationMode": 4, "spacePointWeightExponent": 3.0}, {"parameterEstimationMode": 4, "spacePointWeightExponent": 2.0}]
def maps(t):
    return [dict(trimMapREdges=[float(x) for x in M["rEdges"]], trimMapZEdges=[float(x) for x in M["zEdges"]],
                 trimMapFirst=M["maps"][n]["first"], trimMapLast=M["maps"][n]["last"], trimMapThreshold=t[i]) for i, n in enumerate(("pixel", "strip"))]
v = sys.argv[1]; base, kind = v.split("-", 1)
tools = [dict(d) for d in FIT] if base == "fit" else [{}, {}]
add = {"map08": [dict(m, trimMode=1) for m in maps((0.08, 0.12))],
       "map05": [dict(m, trimMode=1) for m in maps((0.05, 0.08))],
       "res05": [dict(trimMode=2, trimResidualXY=0.5, trimResidualRZ=1e9), dict(maps((0.08, 0.12))[1], trimMode=1)],
       "res08": [dict(trimMode=2, trimResidualXY=0.8, trimResidualRZ=1e9), dict(maps((0.08, 0.12))[1], trimMode=1)],
       "hyb":   [dict(maps((0.08, 0.12))[0], trimMode=3, trimResidualXY=0.5, trimResidualRZ=1e9), dict(maps((0.08, 0.12))[1], trimMode=1)],
       "zcut":  [dict(trimMode=4, trimZMax=2000.), dict(trimMode=4, trimZMax=2000.)],
       "zdw":   [dict(zDownWeightAbove=2000., zDownWeightFactor=0.01), dict(zDownWeightAbove=2000., zDownWeightFactor=0.01)],
       "ends":  [dict(trimMode=5), dict(trimMode=5)],
       "ends6": [dict(trimMode=6), dict(trimMode=6)]}[kind]
for t, a in zip(tools, add): t.update(a)
print(repr(tools).replace(" ", ""))
