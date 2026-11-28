#!/usr/bin/env python3
"""Audit and train strip layer connections on truth, retaining the default pixel table."""
import argparse,collections,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True)
p.add_argument('--table',default='/cvmfs/atlas-nightlies.cern.ch/repo/sw/main_Athena_x86_64-el9-gcc15-opt/2026-11-16T2100/Athena/25.0.80/InstallArea/x86_64-el9-gcc15-opt/share/binTables_ITK_RUN4.txt')
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
t=iter(Path(a.table).read_text().split());n=int(next(t));width=float(next(t));original=[]
for _ in range(n):
    index,stage,src,dst,h,w,nent=[int(next(t)) for _ in range(7)]
    for _ in range(h*w):next(t)
    original.append((src,dst))
isstrip=lambda x:x//1000 in (12,13,14)
base={x for x in original if all(map(isstrip,x))};pixels={x for x in original if not any(map(isstrip,x))}
adj=collections.Counter();skip=collections.Counter();events=tracks=0
def mirror(l):return l+2000 if l//1000==12 else l-2000 if l//1000==14 else l
with open(a.input) as f:
    for line in f:
        e=json.loads(line);events+=1
        for p,ls in zip(e['particles'],e['truth_layers']):
            if not(p[2]==1 and p[3]!=0 and p[4]>900 and abs(p[5])<4 and 0<=p[6]<300 and len(ls)>=3):continue
            tracks+=1
            for step,c in [(1,adj),(2,skip)]:
                for i in range(len(ls)-step):
                    pair=(ls[i+step],ls[i]);c[pair]+=1
                    reflected=tuple(map(mirror,pair))
                    if reflected!=pair:c[reflected]+=1
def write(name,pairs):
    pairs=sorted(pixels|set(pairs));lines=[f'{len(pairs)} {width}']
    for i,(src,dst) in enumerate(pairs):lines.extend([f'{i} 1 {src} {dst} 1 1 100','100'])
    (out/(name+'.txt')).write_text('\n'.join(lines)+'\n')
write('original',base)
variants={}
for threshold in [1,5,20,50,100,250]:
    for mode,c in [('adj',adj),('skip',adj+skip)]:
        kept={p for p,n in c.items() if n>=threshold}
        name=f'{mode}{threshold}';write(name,kept)
        variants[name]={'links':len(kept),'added':sorted(kept-base),'removed':sorted(base-kept)}
    kept=base|{p for p,n in (adj+skip).items() if n>=threshold}
    name=f'aug{threshold}';write(name,kept);variants[name]={'links':len(kept),'added':sorted(kept-base),'removed':[]}
audit={'events':events,'tracks':tracks,'default_links':len(base),'adjacent':[[*p,n] for p,n in adj.most_common()],
       'skip_one':[[*p,n] for p,n in skip.most_common()],'variants':variants}
(out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(f'{events} events, {tracks} training particles; default {len(base)} strip links')
print('Missing observed links (counts include reflection symmetry):')
for pair,n in (adj+skip).most_common():
    if pair not in base:print(pair,n,'adj',adj[pair],'skip',skip[pair])
print('Default links with few observations:')
for pair in sorted(base,key=lambda x:(adj+skip)[x]):
    if (adj+skip)[pair]<100:print(pair,'adj',adj[pair],'skip',skip[pair])
for name,x in variants.items():print(name,x['links'],'added',len(x['added']),'removed',len(x['removed']))
