"""Separate retained truth, hit carriers and hits for conversion/ionisation/decay."""
import argparse
from collections import Counter,defaultdict
from bisect import bisect_right
import json,math
from pathlib import Path
from analyse import rows,identity
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--summary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();summary=json.loads(a.summary.read_text());out={}
for name,run in summary['runs'].items():
    root=Path(run['path']);events=[]
    for ev in range(run['metadata']['events']):
        def file(suffix):
            p=root/f'event{ev:09d}-{suffix}.csv'
            return p if p.exists() else p.with_suffix('.csv.gz')
        truth={identity(r):r for r in rows(file('particles_simulated'))}
        hits=Counter();pixels=Counter()
        for h in rows(file('hits')):
            pid=identity(h);hits[pid]+=1;pixels[pid]+=(int(h['geometry_id'])>>56) in (16,17,18)
        counts=defaultdict(Counter);parents=defaultdict(set)
        for pid,t in truth.items():
            if int(pid[3])==0:continue
            proc=t['process'];parentid=identity(t,'parent_id_');parent=truth.get(parentid)
            if proc not in ('1','2','5'):continue
            m=float(t['m']);p2=sum(float(t[k])**2 for k in ['px','py','pz']);ke=p2/(math.sqrt(p2+m*m)+m) if p2 or m else 0
            keys=[proc+':parent_pdg:'+(parent['particle_type'] if parent else 'unknown'),proc+':parent_process:'+(parent['process'] if parent else 'unknown')]
            if proc=='5':keys.append('5:birth_ke_bin:'+str(bisect_right(summary['edges']['birth_ke_MeV'],ke*1000)))
            for key in keys:
                counts['retained_truth'][key]+=1
                counts['hit_carriers'][key]+=hits[pid]>0
                counts['hits'][key]+=hits[pid]
                counts['pixel_hits'][key]+=pixels[pid]
                if hits[pid]:parents[key].add(parentid)
        counts['parents_with_hit_daughters']=Counter({k:len(v) for k,v in parents.items()})
        events.append(dict(counts))
        print(name,ev,flush=True)
    average={}
    for field in events[0]:
        total=Counter()
        for event in events:total.update(event[field])
        average[field]={k:v/len(events) for k,v in total.items()}
    out[name]={'events':events,'mean':average}
a.output.write_text(json.dumps(out,indent=2))
