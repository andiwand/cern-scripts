#!/usr/bin/env python3
import argparse,json,collections,itertools
from pathlib import Path
import numpy as np
from metrics import selections
p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--output',default='fit-scan.json');p.add_argument('--names',default='raw,nofilter');a=p.parse_args();base=Path(a.directory)
tot=collections.defaultdict(lambda:np.zeros(5,dtype=np.int64));events=0
cuts=list(itertools.product([.1,.3,1.,3.,10.,100.,1e9],[2.,3.,5.,10.,1e9],[1.1,1e9]))
with open(base/'seeds.jsonl') as sin,open(base/'fits.jsonl') as fin:
 for sl,fl in zip(sin,fin):
  e=json.loads(sl);f=json.loads(fl);assert e['event']==f['event'];events+=1
  target={i for i,p in enumerate(e['particles']) if selections(p)['seedable']}
  for name in a.names.split(','):
   seeds=e['seeds'][name];fits=f['fits'][name];rows=np.array([[float('inf') if v is None else float(v) for v in r[:8]] for r in fits]);ndf=np.array([max(1,2*s[0]-5) for s in seeds]);chi=rows[:,1]/ndf;sig=np.maximum(rows[:,2]-5.,0.)/np.maximum(rows[:,4],1e-6)
   for q,ip,tol in cuts:
    mask=(rows[:,0]>0)&(chi<q)&(sig<ip)&(rows[:,6]<tol)&(np.abs(rows[:,3])<200.)
    chosen=np.flatnonzero(mask);owner={}
    for i in chosen:
     for sp in seeds[i][9]:owner.setdefault(sp,i)
    selected=[i for i in chosen if sum(owner[sp]!=i for sp in seeds[i][9])<=.9*len(seeds[i][9])]
    got={t for i in selected for t in seeds[i][3]}&target;pure={t for i in selected for t in seeds[i][4]}&target
    tot[(name,q,ip,tol)]+=np.array([len(selected),sum(not seeds[i][3] for i in selected),len(got),len(pure),len(target)])
  print('Event',events,flush=True)
out=[dict(name=n,chi=q,d0sigma=ip,tolerance=t,seeds=int(v[0]),unmatched=int(v[1]),found=int(v[2]),pure=int(v[3]),den=int(v[4]),events=events,efficiency=v[2]/v[4],pure_efficiency=v[3]/v[4],fake_rate=v[1]/max(1,v[0])) for (n,q,ip,t),v in tot.items()]
(base/a.output).write_text(json.dumps(out,indent=2)+'\n')
for x in sorted(out,key=lambda x:x['fake_rate']):
 if x['efficiency']>.86:print(x)
