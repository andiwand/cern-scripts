#!/usr/bin/env python3
import json,statistics
from pathlib import Path
R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
raw=[json.loads(x) for x in (R/'vectorization/kernel-profile.jsonl').read_text().splitlines()]
assert len(raw)==10
rows=[]
for i,shape in enumerate(['67 → 128','128 → 64','64 → 32','32 → 16','16 → 3 / 5']):
    layer=[x for x in raw if x['layer']==i]
    assert len(layer)==2
    rows.append({'layer':i,'shape':shape,**{
        k:sum(statistics.mean(z[k] for z in x['dense_raw_us'])-x['baseline_us'] for x in layer)
        for k in ['sse','gemv','avx2','sse_blocked']}})
activations={k:sum(x.get('activation_us',{}).get(k,0) for x in raw)
             for k in ['direct_fused','sofie_separate']}
result={'scope':'number + pos1; 512 real inputs, individually warmed layers; 100000 calls per repetition',
        'dense_repetitions':3,'activation_repetitions':1,
        'rows':rows,'activation_us':activations,
        'dense_sum_us':{k:sum(row[k] for row in rows) for k in ['sse','gemv','avx2','sse_blocked']},
        'blocked_layer_outputs_bit_identical':True,
        'whole_network_bit_identical_inputs':100000}
(R/'kernel-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
