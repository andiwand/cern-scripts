#!/usr/bin/env python3
"""Test retained-only clone suppression on the full GBTS candidate list."""
import argparse,collections,json,itertools,math
from pathlib import Path
from metrics import selections
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',required=True);a=p.parse_args()
totals=collections.defaultdict(collections.Counter);nev=0
for line in open(a.input):
 e=json.loads(line);nev+=1
 target={i for i,p in enumerate(e['particles']) if selections(p)['seedable']}
 for name,ss in e['seeds'].items():
  if 'raw' not in name and not name.startswith('t'):continue
  for mode,share,cut in itertools.product(['static','greedy'],[.49,.67,.9],['none','z150','z125','tol110','tol110_z150','tol105_z150','d20_z150','d50_z150']):
   seeds=[]
   for s in ss:
    par=s[7]
    z=125 if 'z125' in cut else 150 if 'z150' in cut else math.inf
    tol=1.1 if 'tol110' in cut else 1.05 if 'tol105' in cut else math.inf
    d=20 if 'd20' in cut else 50 if 'd50' in cut else math.inf
    if cut!='none' and not (par[2] is not None and par[3] is not None and par[4] is not None and par[2]<d and abs(par[3])<z and par[4]<tol):continue
    seeds.append(s)
   seeds.sort(key=lambda s:s[8])
   owner={}
   if mode=='static':
    for i,s in enumerate(seeds):
     for sp in s[9]:owner.setdefault(sp,i)
   accepted=[]
   for i,s in enumerate(seeds):
    taken=sum(sp in owner and owner[sp]!=i for sp in s[9])
    if taken>share*len(s[9]):continue
    accepted.append(s)
    if mode=='greedy':
     for sp in s[9]:owner.setdefault(sp,i)
   got={i for s in accepted for i in s[3]}&target
   c=totals[(name,mode,share,cut)];c['seeds']+=len(accepted);c['unmatched']+=sum(not s[3] for s in accepted);c['found']+=len(got);c['den']+=len(target)
out=[]
for (name,mode,share,cut),c in totals.items():
 out.append(dict(name=name,mode=mode,share=share,cut=cut,**c,efficiency=c['found']/c['den'],fake_rate=c['unmatched']/max(1,c['seeds']),events=nev))
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
for x in sorted(out,key=lambda x:-x['efficiency']):
 if x['efficiency']>.86 and x['fake_rate']<.5:print(x)
