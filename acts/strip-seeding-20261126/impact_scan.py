#!/usr/bin/env python3
"""Offline cuts on diagnostic three-point circles, before choosing implementation."""
import argparse,collections,json,itertools
from pathlib import Path
import numpy as np
from metrics import selections
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',default='impact-scan.json');a=p.parse_args()
cuts=list(itertools.product([5.,10.,20.,50.,1e6],[100.,150.,200.,250.,1e6],[1.0,1.1,1.5,1e6]))
totals=collections.defaultdict(lambda:np.zeros(5,dtype=np.int64));n_events=0
with open(a.input) as f:
    for line in f:
        e=json.loads(line);n_events+=1
        target={i for i,p in enumerate(e['particles']) if selections(p)['seedable']}
        for name,seeds in e['seeds'].items():
            n=len(seeds);params=np.array([[float('inf') if x is None else x for x in s[7]] for s in seeds])
            matched=np.array([bool(s[3]) for s in seeds]);linked=np.array([s[5] for s in seeds]);
            for raw in [False,True]:
                for d,z,t in cuts:
                    if raw and t!=1e6:continue
                    mask=(params[:,0 if raw else 2]<d)&(abs(params[:,1 if raw else 3])<z)&(params[:,4]<t if t<1e6 else True)
                    got=set(i for j in np.flatnonzero(mask) for i in seeds[j][3])&target
                    key=(name,raw,d,z,t);totals[key]+=np.array([mask.sum(),(mask&~matched&linked).sum(),(mask&~linked).sum(),len(got),len(target)])
out=[]
for (name,raw,d,z,t),v in totals.items():
    n,f,u,found,den=map(int,v);out.append(dict(name=name,raw=raw,d0=d,z0=z,tolerance=t,seeds=n,unmatched=f+u,efficiency=found/max(1,den),fake_rate=(f+u)/max(1,n),found=found,denominator=den,events=n_events))
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
for name in sorted({x['name'] for x in out}):
    rows=[x for x in out if x['name']==name]
    # Pareto frontier; cost is unmatched fraction, reward is efficiency.
    frontier=[];best=-1
    for x in sorted(rows,key=lambda x:(x['fake_rate'],-x['efficiency'])):
        if x['efficiency']>best:frontier.append(x);best=x['efficiency']
    print(name)
    for x in frontier:
        if x['efficiency']>.75:print('  ', 'raw' if x['raw'] else 'cal','d0',x['d0'],'z0',x['z0'],'tol',x['tolerance'],f'eff {100*x["efficiency"]:.3f}% unmatched {100*x["fake_rate"]:.3f}% seeds/ev {x["seeds"]/n_events:.1f}')
