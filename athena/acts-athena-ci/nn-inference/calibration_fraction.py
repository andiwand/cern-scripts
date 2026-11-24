#!/usr/bin/env python3
"""Diagnostic counterfactual from the existing five-event profiles, not a raw A/B."""
import json
import tarfile
from pathlib import Path

R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
result={}
for backend in ['original','direct_avx2','sofie_gemv']:
    run=R/'profiles'/backend
    with tarfile.open(run/'perfmonmt_RAWtoALL.json.tar.gz') as archive:
        data=json.load(archive.extractfile(archive.getmembers()[0]))
    components=data['componentLevel']
    ckf_wall_ms=sum(components[stage]['ActsTrackFindingAlg']['wallTime'] for stage in ['FirstEvent','Execute'])
    ckf_cpu_ms=sum(components[stage]['ActsTrackFindingAlg']['cpuTime'] for stage in ['FirstEvent','Execute'])
    rows=[json.loads(line) for line in (run/'profile.jsonl').read_text().splitlines()]
    calibration_ms=sum(sum(row['nanoseconds']) for row in rows)/1e6
    table=(run/'log.RAWtoALL').read_text().split('INFO statistics:',1)[1].split('INFO Ratios:',1)[0]
    used_seeds=int(next(line for line in table.splitlines() if 'Used   seeds' in line).split('|')[-2])
    calls=sum(row['counts'][0] for row in rows)
    result[backend]={'events':5,'includes_first_event':True,'ckf_wall_ms':ckf_wall_ms,
                     'ckf_cpu_ms':ckf_cpu_ms,'calibration_wall_ms':calibration_ms,
                     'used_seeds':used_seeds,'calibration_calls':calls,
                     'calibrations_per_used_seed':calls/used_seeds,
                     'ckf_wall_us_per_used_seed':ckf_wall_ms*1000/used_seeds,
                     'calibration_wall_us_per_used_seed':calibration_ms*1000/used_seeds,
                     'calibration_fraction':calibration_ms/ckf_wall_ms,
                     'counterfactual_overhead':calibration_ms/(ckf_wall_ms-calibration_ms)}
result['assumption']='Estimate only: subtract the timed calibration block, assuming unchanged tracking work and other costs. This is not the measured uncalibrated configuration.'
(R/'calibration-fraction.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
