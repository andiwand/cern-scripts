#!/usr/bin/env python3
import argparse,collections,json,itertools
from pathlib import Path
from metrics import selections
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',required=True);a=p.parse_args()
tot=collections.defaultdict(lambda:[0,0,0,0]);ne=0
for line in open(a.input):
 e=json.loads(line);ne+=1;target={i for i,p in enumerate(e['particles']) if selections(p)['seedable']}
 for name,ss in e['seeds'].items():
  if 'raw' not in name and not name.startswith('t'):continue
  owner={}
  for i,s in enumerate(ss):
   for sp in s[9]:owner.setdefault(sp,i)
  for sh in [.49,.67,.9]:
   accepted=[s for i,s in enumerate(ss) if sum(owner[sp]!=i for sp in s[9])<=sh*len(s[9])]
   for q in [-4.,-5.,-6.,-7.,-7.5,-8.,-8.5,-9.,-9.5,-10.]:
    selected=[s for s in accepted if s[8]<=q];got={i for s in selected for i in s[3]}&target
    c=tot[(name,sh,q)];c[0]+=len(selected);c[1]+=sum(not s[3] for s in selected);c[2]+=len(got);c[3]+=len(target)
out=[dict(name=n,share=s,quality=q,seeds=v[0],unmatched=v[1],found=v[2],den=v[3],efficiency=v[2]/v[3],fake_rate=v[1]/max(1,v[0]),events=ne) for (n,s,q),v in tot.items()]
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
for x in sorted(out,key=lambda x:-x['efficiency']):
 if x['efficiency']>.85 and x['fake_rate']<.48:print(x)
