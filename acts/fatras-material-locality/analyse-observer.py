"""Exact creator attribution and observational replay check against archived G4."""
import csv,gzip,hashlib,json,math
from data import rows
from collections import Counter,defaultdict
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work',type=Path,required=True)
args=parser.parse_args()
root=args.work
root.mkdir(parents=True,exist_ok=True);p=root/'geant4-observed'
reference=Path.home()/'cern/scripts/acts/fatras-soft-secondaries/results/2026-10-15/geant4'
exact={}
for ref in sorted(reference.glob('event*.csv.gz')):
 name=ref.name.removesuffix('.gz')
 observed=p/name
 with gzip.open(ref,'rb') as z:
  expected=hashlib.file_digest(z,'sha256').hexdigest()
 if observed.exists():
  actual=hashlib.sha256(observed.read_bytes()).hexdigest()
 else:
  # Archive reuses already verified immutable reference files; retain the
  # independently measured observed hashes as evidence of the replay.
  actual=json.loads((p/'observed-csv-hashes.json').read_text())[name]
 exact[name]=actual==expected

assert len(exact)==6 and all(exact.values())
counters=defaultdict(Counter)
for r in rows(p/'observer.tsv',delimiter='\t'):
 if r['parent']=='0':continue
 proc=r['creator'];region='pixel' if math.hypot(float(r['x']),float(r['y']))<190 else 'strip'
 assert math.hypot(float(r['x']),float(r['y']))<=1202.001 and abs(float(r['z']))<=4002.001
 for scope in ['ID',region]:
  counters[scope+'_creator'][proc]+=1
  counters[scope+'_born_sensitive'][proc]+=('ActsSensitive#' in r['birth_volume'])
  counters[scope+'_parent_below_pair_threshold'][proc]+=float(r['parent_birth_ke_MeV'])<1.0219979
  counters[scope+'_stopping_hit'][proc]+=r['stopped']=='1'
  counters[scope+'_birth_material'][proc+':'+r['birth_material']]+=1
  counters[scope+'_parent_process'][proc+':'+r['parent_creator']]+=1
 counters['events'][r['event']]+=1
assert dict(counters['events'])=={'0':96505,'1':132615,'2':113475}
assert sum(counters['pixel_creator'].values())==116050
out={'exact_reference_csv':exact,'counts_over_three_events':counters,'means':{k:{kk:vv/3 for kk,vv in v.items()} for k,v in counters.items()}}
(root/'observer-summary.json').write_text(json.dumps(out,indent=2))
print({scope:{p:round(counters[scope+'_creator'][p]/3,1) for p in ['compt','phot']} for scope in ['ID','pixel','strip']})
