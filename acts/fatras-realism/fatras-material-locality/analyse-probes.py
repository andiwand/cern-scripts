"""All primary hit counts for the controlled electron starts; no hit selection."""
import argparse,csv,json
from data import rows
from collections import Counter,defaultdict
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);a=p.parse_args();root=a.work
probes={str(p['particle']):p for p in json.loads((root/'probe-input/probes.json').read_text())['particles']}
out={}
for name in ['probe-fatras','probe-vacuum','probe-geant4-observed']:
 hits=Counter();sensors=defaultdict(set)
 for r in rows(root/name/'event000000000-hits.csv'):
   if int(r['particle_id_gen'])==0:
    hits[r['particle_id_part']]+=1;sensors[r['particle_id_part']].add(r['geometry_id'])
 counts=defaultdict(Counter)
 for ident,probe in probes.items():
  key=str(probe['kinetic_MeV'])+':'+probe['origin']
  counts[key]['hits']+=hits[ident];counts[key]['carriers']+=hits[ident]>0
  counts[key]['input']+=1;counts[key]['unique_sensors']+=len(sensors[ident])
 assert sum(c['input'] for c in counts.values())==2400
 out[name]=dict(counts)
(root/'probe-summary.json').write_text(json.dumps(out,indent=2))
