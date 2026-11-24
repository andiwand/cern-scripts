#!/usr/bin/env python3
import gzip,json,math,sys
from pathlib import Path
R=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/physics')
def load(backend):
    with gzip.open(R/backend/'outcomes.txt.gz','rt') as stream:
        rows=[s.split() for s in stream]
    return {tuple(r[:4]):r for r in rows if r[0]=='R'},sorted(r for r in rows if r[0]!='R')
backend=sys.argv[1] if len(sys.argv)>1 else 'Native'
a,at=load('OnnxRuntime');b,bt=load(backend);assert a.keys()==b.keys()
result={'tracks':len(a),'truth_and_event_records_equal':at==bt,
        'non_kinematic_track_records_equal':all(a[k][:7]+a[k][13:]==b[k][:7]+b[k][13:] for k in a),'differences':{}}
for index,name in enumerate(['pt_MeV','eta','phi','d0_mm','z0_mm','chi2'],7):
    differences=[];relative=[]
    for key in a:
        x,y=float(a[key][index]),float(b[key][index]);d=abs(y-x)
        if name=='phi':d=abs(math.remainder(y-x,2*math.pi))
        differences.append(d);relative.append(d/max(abs(x),1e-20))
    differences.sort();relative.sort()
    result['differences'][name]={'max_abs':differences[-1],'p99_abs':differences[int(.99*len(differences))],'max_relative':relative[-1]}
(R/('record-comparison'+('' if backend=='Native' else '-'+backend)+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
