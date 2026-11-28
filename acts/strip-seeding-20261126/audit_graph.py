#!/usr/bin/env python3
import argparse,collections,json
from pathlib import Path
from metrics import selections
p=argparse.ArgumentParser();p.add_argument('directory');a=p.parse_args();base=Path(a.directory)
tot=collections.Counter();eta=collections.defaultdict(collections.Counter);ev=[]
for line in open(base/'seeds.jsonl'):
 e=json.loads(line);g=json.loads((base/f'graph_tuned_{e["run"]}_{e["event"]}.json').read_text())
 target={i for i,p in enumerate(e['particles']) if selections(p)['seedable']}
 sp={s[0]:set(s[7]) for s in e['sp_data']};layers={s[0]:s[1] for s in e['sp_data']}
 accepted=collections.defaultdict(set)
 for s in g['nodes']:
  for t in sp[s]:accepted[t].add(layers[s])
 present={t for t,ls in accepted.items() if len(ls)>=3}
 edge_truth=[sp[x]&sp[y] for x,y,_ in g['edges']]
 doublets=set().union(*edge_truth);triplets=set()
 ends=collections.defaultdict(set);starts=collections.defaultdict(set)
 for (x,y,_),truth in zip(g['edges'],edge_truth):
  ends[y]|=truth;starts[x]|=truth
 chainable=set().union(*(ends[k]&starts[k] for k in ends))
 for i,(x,y,neis) in enumerate(g['edges']):
  for j in neis:
   u,v,_=g['edges'][j]
   assert len({x,y,u,v})==3
   triplets|=edge_truth[i]&edge_truth[j]
 got={n:{i for s in ss for i in s[3]}&target for n,ss in e['seeds'].items()}
 stages={'inserted':present&target,'doublet':doublets&target,'two_doublets':chainable&target,'triplet':triplets&target,**got}
 row={k:len(v) for k,v in stages.items()};row['target']=len(target);counts=collections.Counter()
 for i in got['legacy']-got['tuned']:
  reason=('no_nodes' if i not in present else 'no_doublet' if i not in doublets else 'no_two_doublets' if i not in chainable else 'triplet_link_cut' if i not in triplets else 'filter_or_path' if i not in got['raw'] else 'clone_or_split')
  counts[reason]+=1;eta[int(abs(e['particles'][i][5])*2)][reason]+=1
  if reason=='filter_or_path' and i in got['nofilter']:counts['filter_or_path_recovered_without_filter']+=1
 row['legacy_only_reasons']=dict(counts);tot.update(counts);ev.append(row)
print('Stage coverage', {k:sum(e.get(k,0) for e in ev) for k in ev[0] if k!='legacy_only_reasons'})
print('Legacy-only losses',dict(tot));print('Eta half-unit bins',dict(eta))
(base/'graph-audit.json').write_text(json.dumps({'events':ev,'legacy_only':dict(tot),'eta':dict(eta)},indent=2)+'\n')
