#!/usr/bin/env python3
"""Final event-bootstrap comparison and standalone scientific plots."""
import argparse,json,re
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('summary');p.add_argument('--log');p.add_argument('--plots',action='store_true');p.add_argument('--names');p.add_argument('--refiners');a=p.parse_args()
path=Path(a.summary);d=json.loads(path.read_text());N=d['events'];rows=[]
if a.names:d['totals']={k:v for k,v in d['totals'].items() if k in a.names.split(',')}
refiners=json.loads(Path(a.refiners).read_text()) if a.refiners else {}
rng=np.random.default_rng(20261126);indices=rng.integers(N,size=(4000,N))
boots={};cpu={}
if a.log:
 for line in Path(a.log).read_text().splitlines():
  m=re.search(r'INFO Execute\s+(\d+)\s+([0-9.]+).*?\s(\S+)\s*$',line)
  if m:cpu[m[3]]=float(m[2])/int(m[1])
for name,c in d['totals'].items():
 vals=np.array([[e['results'][name].get(k,0) for k in ['seedable_num','seedable_den','fake','unlinked','seeds']] for e in d['per_event']])
 bs=vals[indices].sum(axis=1)
 b=np.column_stack([bs[:,0]/bs[:,1],(bs[:,2]+bs[:,3])/bs[:,4],(bs[:,2]+bs[:,3])/N]);boots[name]=b
 row=dict(name=name,efficiency=c['seedable_num']/c['seedable_den'],unmatched_fraction=(c['fake']+c['unlinked'])/c['seeds'],fake_fraction=c['fake']/c['seeds'],unlinked_fraction=c['unlinked']/c['seeds'],seeds_per_event=c['seeds']/N,unmatched_per_event=(c['fake']+c['unlinked'])/N,duplicate_fraction=c['seedable_dup']/max(1,c['seedable_num']),barrel_efficiency=c['barrel_num']/c['barrel_den'],prompt_efficiency=c['prompt_num']/c['prompt_den'],pure_efficiency=c['seedable_pure']/c['seedable_den'],pure_seed_fraction=c['pure']/c['seeds'],efficiency_ci=np.quantile(b[:,0],[.025,.975]).tolist(),unmatched_fraction_ci=np.quantile(b[:,1],[.025,.975]).tolist(),cpu_ms=cpu.get('ActsSeed_'+name))
 if name in refiners:row['cpu_ms']=cpu['ActsSeed_'+refiners[name]['InputSeeds']]+cpu['Refine_'+name]
 if name=='legacy':row['cpu_ms']=float(np.mean([e['legacy_cpu_ms'] for e in d['per_event'][1:]]))
 rows.append(row)
comparisons=[]
for row in rows:
 for base in ['gbts','legacy','tuned']:
  if base not in boots or base==row['name']:continue
  b=boots[row['name']]-boots[base]
  comparisons.append(dict(name=row['name'],reference=base,efficiency_difference_ci_pp=(100*np.quantile(b[:,0],[.025,.975])).tolist(),unmatched_fraction_difference_ci_pp=(100*np.quantile(b[:,1],[.025,.975])).tolist(),unmatched_per_event_difference_ci=np.quantile(b[:,2],[.025,.975]).tolist()))
out={'events':N,'denominator':next(iter(d['totals'].values()))['seedable_den'],'rows':rows,'paired_bootstrap':comparisons,'cpu_ms':cpu}
(path.parent/'comparison.json').write_text(json.dumps(out,indent=2)+'\n')
print('variant | efficiency % | unmatched % | unmatched/event | seeds/event | duplicates % | CPU ms/event')
for r in rows:print(f'{r["name"]} | {100*r["efficiency"]:.2f} | {100*r["unmatched_fraction"]:.2f} | {r["unmatched_per_event"]:.1f} | {r["seeds_per_event"]:.1f} | {100*r["duplicate_fraction"]:.1f} | {r["cpu_ms"] or 0:.1f}')
if a.plots:
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 colors={'gbts':'#777777','grid':'#1f77b4','legacy':'#222222','tuned':'#d62728','high_efficiency':'#9467bd','purity':'#2ca02c'}
 labels={'gbts':'GBTS original','grid':'Grid triplet','legacy':'Legacy','tuned':'GBTS balanced','high_efficiency':'GBTS efficiency','purity':'GBTS purity'}
 labels.update(chi4='GBTS relaxed filter',fit3='Strip fit (3σ)',fit5='Strip fit (5σ)')
 colors.update(chi4='#ed951c',fit3='#2ca02c',fit5='#9467bd')
 fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
 for ax,key,xlabel in [(axs[0,0],'eta',r'Truth $|\eta|$'),(axs[0,1],'pt','Truth pT bin [GeV]'),(axs[1,0],'z','Truth production |z| [mm]')]:
  edges=np.array(d[key+'_edges']);nb=len(edges)-1
  if key=='z':nb-=1
  for name,c in d['totals'].items():
   den=np.array([c.get(f'{key}{i}_den',0) for i in range(nb)]);num=np.array([c.get(f'{key}{i}_num',0) for i in range(nb)]);ok=den>=(100 if key=='eta' else 1)
   x=np.arange(nb) if key=='pt' else (edges[:nb]+edges[1:nb+1])/2
   y=np.divide(num,den,out=np.zeros(nb),where=ok)
   errors=[]
   for i in np.flatnonzero(ok):
    vals=np.array([[e['results'][name].get(f'{key}{i}_num',0),e['results'][name].get(f'{key}{i}_den',0)] for e in d['per_event']]);bs=vals[indices].sum(axis=1);bs=bs[bs[:,1]>0]
    lo,hi=np.quantile(bs[:,0]/bs[:,1],[.025,.975]);errors.append([max(0.,y[i]-lo),max(0.,hi-y[i])])
   ax.errorbar(x[ok],100*y[ok],yerr=100*np.array(errors).T,fmt='o-' if name!='legacy' else 'x--',label=labels.get(name,name),color=colors.get(name),ms=4,lw=1.3,elinewidth=.7)
  ax.set(xlabel=xlabel,ylabel='Strip seed efficiency [%]',ylim=(0 if key=='z' else 40,100));ax.grid(alpha=.2)
  if key=='pt':ax.set_xticks(np.arange(1,nb),[f'{lo:g}–{hi:g}' if hi<1000 else f'≥{lo:g}' for lo,hi in zip(edges[1:-1],edges[2:])],fontsize=8)
  if key=='eta':ax.set_title('Bins with ≥100 truth particles; sparse tail in report',fontsize=9)
 ax=axs[1,1]
 for r in rows:ax.errorbar(r['unmatched_per_event'],100*r['efficiency'],yerr=[[100*(r['efficiency']-r['efficiency_ci'][0])],[100*(r['efficiency_ci'][1]-r['efficiency'])]],fmt='o',label=labels.get(r['name'],r['name']),color=colors.get(r['name']))
 ax.set(xlabel='Unmatched seeds per event',ylabel='Strip seed efficiency [%]');ax.grid(alpha=.2)
 axs[0,0].legend(fontsize=8);axs[1,1].legend(fontsize=8)
 fig.suptitle(f'Strip-only seeding, {N} held-out full-truth events; 95% event-bootstrap intervals\nCharged stable truth: pT > 1 GeV, production r < 300 mm, ≥3 strip layers',fontsize=11)
 for ext in ['png','pdf']:fig.savefig(path.parent/('comparison.'+ext),dpi=170)
