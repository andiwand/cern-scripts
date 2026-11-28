#!/usr/bin/env python3
"""Count seed matches with identical denominators; retain event-level paired counts."""
import argparse,collections,json,math
from pathlib import Path
from metrics import selections
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',default='summary.json');args=p.parse_args()
eta_edges=[0,.3,.6,1.,1.5,2.,2.5,2.7,4.]
pt_edges=[.9,1.,1.5,2.,3.,5.,10.,1000.]
z_edges=[0.,50.,100.,150.,200.,100000.]
r_edges=[0.,1.,10.,100.,300.]
totals=collections.defaultdict(collections.Counter)
events=[]
def consume(c,parts,seeds):
    matches=collections.Counter(i for s in seeds for i in s[3]);pure={i for s in seeds for i in s[4]}
    c['seeds']+=len(seeds)
    for s in seeds:
        cls='matched' if s[3] else 'fake' if s[5] else 'unlinked'
        c[cls]+=1;c['pure']+=bool(s[4]);c[f'size{s[0]}_{cls}']+=1
        for k,(lo,hi) in enumerate(zip(eta_edges,eta_edges[1:])):
            if lo<=abs(s[1])<hi:c[f'eta{k}_seeds']+=1;c[f'eta{k}_{cls}']+=1
    for i,part in enumerate(parts):
        for sel,yes in selections(part).items():
            if not yes:continue
            c[sel+'_den']+=1;c[sel+'_num']+=i in matches;c[sel+'_pure']+=i in pure;c[sel+'_dup']+=matches[i]>1
        if selections(part)['seedable']:
            for ax,edges,x in [('eta',eta_edges,abs(part[5])),('pt',pt_edges,part[4]/1000),('z',z_edges,abs(part[7])),('r',r_edges,part[6])]:
                for k,(lo,hi) in enumerate(zip(edges,edges[1:])):
                    if lo<=x<hi:c[f'{ax}{k}_den']+=1;c[f'{ax}{k}_num']+=i in matches
    return {s:sorted(i for i,x in enumerate(parts) if selections(x)[s] and i in matches) for s in ['seedable','barrel']}
with open(args.input) as f:
    for line in f:
        e=json.loads(line);row={'event':e['event'],'results':{},'matched':{}}
        for name,seeds in e['seeds'].items():
            c=collections.Counter();row['matched'][name]=consume(c,e['particles'],seeds)
            totals[name].update(c);row['results'][name]=dict(c)
        if 'legacy_cpu_ms' in e:row['legacy_cpu_ms']=e['legacy_cpu_ms']
        events.append(row)
out={'events':len(events),'eta_edges':eta_edges,'pt_edges':pt_edges,'z_edges':z_edges,'r_edges':r_edges,'totals':dict(totals),'per_event':events}
Path(args.output).write_text(json.dumps(out,indent=2)+'\n')
print(f'{len(events)} events. Matched: >=3 SPs and >=50%; SP truth: intersection of both cluster contributors.')
print('Efficiencies use charged status-1 truth, pT>1 GeV, production r<300 mm; seedable needs >=3 distinct strip layers.')
print(f'{"variant":24} {"seeds/ev":>9} {"fake%":>8} {"unlinked%":>10} {"unmatched%":>11} {"seedable%":>10} {"common%":>9} {"barrel%":>9} {"dup%":>8}')
for name,c in totals.items():
    pct=lambda n,d:100*c[n]/max(1,c[d])
    print(f'{name:24} {c["seeds"]/len(events):9.1f} {pct("fake","seeds"):8.3f} {pct("unlinked","seeds"):10.3f} {100*(c["fake"]+c["unlinked"])/max(1,c["seeds"]):11.3f} {pct("seedable_num","seedable_den"):10.3f} {pct("common_num","common_den"):9.3f} {pct("barrel_num","barrel_den"):9.3f} {pct("seedable_dup","seedable_num"):8.3f}')
print('Seedable denominators:',{k:c['seedable_den'] for k,c in totals.items()})
print('Efficiency by |eta|:')
for k,(lo,hi) in enumerate(zip(eta_edges,eta_edges[1:])):
    print(f'{lo:3.1f}-{hi:3.1f} '+ ' '.join(f'{n}={100*c[f"eta{k}_num"]/max(1,c[f"eta{k}_den"]):.2f}% ({c[f"eta{k}_den"]})' for n,c in totals.items()))
