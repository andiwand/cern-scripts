"""Balanced serial CKF timing runs, with per-process warm-up excluded in analysis."""
import os,subprocess,json,time
from pathlib import Path
base=Path(os.environ.get('ACTS_EDM_EXPERIMENT_ROOT', '/private/tmp/acts-edm-2026-10-31'));out=base/'results'/'timing';out.mkdir(exist_ok=True)
orders=[['main','vector','any'],['vector','any','main'],['any','main','vector'],['any','vector','main'],['vector','main','any'],['main','any','vector']]
for workload,events,runs,args in [('muons',20,8,[]),('ttbar-pu200',3,6,['--ttbar'])]:
 for block,order in enumerate(orders):
  for variant in order:
   dest=out/workload/f'{variant}-{block}';dest.mkdir(parents=True,exist_ok=True)
   env=os.environ.copy();env.update(CKF_EVENTS=str(events),CKF_RUNS=str(runs),CKF_RECORD_MATERIAL_STATES='0',CKF_PILEUP='200')
   env.pop("EDM_VALIDATE",None)
   start=time.time();print(workload,block,variant,flush=True)
   with (dest/'log.txt').open('w') as log:
    run=subprocess.run(['bash',str(base/'run-one.sh'),variant,str(dest),*args],env=env,stdout=log,stderr=subprocess.STDOUT)
   (dest/'run.json').write_text(json.dumps({'variant':variant,'block':block,'events':events,'rounds':runs,'start':start,'wall_s':time.time()-start,'returncode':run.returncode},indent=2))
   if run.returncode:raise SystemExit(f'{variant} failed: {dest}/log.txt')
