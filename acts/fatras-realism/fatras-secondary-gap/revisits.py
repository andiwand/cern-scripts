"""Audit repeated sensor visits; time-sort per carrier/sensor, not CSV row order."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from analyse import rows, identity

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--summary',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
s=json.loads(a.summary.read_text())
out={}
for name,run in s['runs'].items():
    root=Path(run['path']);events=[]
    for ev in range(run['metadata']['events']):
        def file(suffix):
            path=root/f'event{ev:09d}-{suffix}.csv'
            return path if path.exists() else path.with_suffix('.csv.gz')
        truth={identity(r):r['process'] for r in rows(file('particles_simulated'))}
        visits=defaultdict(list);volumes=defaultdict(list)
        for h in rows(file('hits')):
            if int(h['particle_id_gen'])==0:continue
            pid=identity(h);geo=h['geometry_id']
            visits[(pid,geo)].append(tuple(float(h[k]) for k in ['tt','tx','ty','tz']))
            volumes[int(geo)>>56].append((float(h['tz']),math.hypot(float(h['tx']),float(h['ty']))))
        count=Counter()
        for (pid,geo),hits in visits.items():
            proc=truth[pid];reg='pixel' if int(geo)>>56 in (16,17,18) else 'strip'
            hits.sort()
            for prev,cur in zip(hits,hits[1:]):
                local=math.dist(prev[1:],cur[1:])<1
                quick=(cur[0]-prev[0])/299.792458<1
                for scope in ['ID',reg]:
                    count[scope+':'+proc+':all']+=1
                    count[scope+':'+proc+':within_1mm']+=local
                    count[scope+':'+proc+':within_1ns']+=quick
                    count[scope+':'+proc+':both']+=local and quick
        events.append(dict(count))
        if ev==0:
            print(name,'volume (minZ,maxZ,minR,maxR)',{v:[min(x[0] for x in xs),max(x[0] for x in xs),min(x[1] for x in xs),max(x[1] for x in xs)] for v,xs in volumes.items()},flush=True)
    total=Counter()
    for event in events:total.update(event)
    out[name]={'events':events,'mean':{k:v/len(events) for k,v in total.items()}}
a.output.write_text(json.dumps(out,indent=2))
