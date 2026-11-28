import os
import csv,json,statistics
from pathlib import Path
base=Path(os.environ.get('ACTS_EDM_EXPERIMENT_ROOT', '/private/tmp/acts-edm-2026-10-31'))/'results';report={}
for workload in ['muons','ttbar-pu200']:
 d={}
 for variant in ['main','vector','any']:
  blocks=[]
  for i in range(6):
   p=base/'timing'/workload/f'{variant}-{i}'
   rows=list(csv.DictReader((p/'times.csv').open()))
   assert len(rows)==(8 if workload=='muons' else 6), p
   expected=f'build-{variant}/python/acts/__init__.py'
   assert expected in (p/'log.txt').read_text().splitlines()[0], p
   assert json.loads((p/'run.json').read_text())['returncode']==0, p
   med={key:statistics.median(float(r[key]) for r in rows[1:]) for key in rows[0]}
   blocks.append(med)
  d[variant]={'block_medians_s':blocks,'median_ckf_s':statistics.median(b['ckf'] for b in blocks)}
 for variant in ['vector','any']:
  ratios=[d[variant]['block_medians_s'][i]['ckf']/d['main']['block_medians_s'][i]['ckf'] for i in range(6)]
  d[variant]['paired_ckf_ratios']=ratios;d[variant]['median_ratio']=statistics.median(ratios)
 report[workload]=d
(base/'timing-summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
