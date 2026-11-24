#!/usr/bin/env python3
"""Empirical dense-arithmetic bounds; nonlinear operations are not FLOP-counted."""
import collections
import json
import statistics as st
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
R=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn')
O=R/'roofline'
timing=json.loads((R/'optimization/general-summary.json').read_text())
models={}
for name,out in [('number',3),('pos1',5),('pos2',10),('pos3',15)]:
 dims=[67,128,64,32,16,out]
 weights=sum(a*b for a,b in zip(dims,dims[1:]));bias=sum(dims[1:])
 models[name]={'weights':weights,'biases':bias,'parameter_bytes':4*(weights+bias),'dense_flops':2*weights}
pair={k:models['number'][k]+models['pos1'][k] for k in ['parameter_bytes','dense_flops']}
pair['intensity_flop_per_byte']=pair['dense_flops']/pair['parameter_bytes']
result={'models':models,'number_plus_pos1':pair,'all_model_parameter_bytes':sum(v['parameter_bytes'] for v in models.values()),
        'scope':'Threadripper 3970X core 16; GCC 15.2 O2. Empirical warm per-core read/compute microbenchmarks. Dense multiply-add counts as two FLOPs; exp, division, normalization, softmax and other work are excluded from the FLOP numerator. Bounds are for dense arithmetic, not attainable whole-network latency.',
        'cache_per_core':{'L1D_bytes':32768,'L2_bytes':524288,'shared_L3_bytes':16777216},'backends':{}}
fig,ax=plt.subplots(figsize=(7.6,4.8),layout='constrained');xs=np.geomspace(.05,4,300)
for isa,color in [('sse','#2563a6'),('avx2','#cf6a15')]:
 rows=[json.loads(s) for s in (O/(isa+'.jsonl')).read_text().splitlines()]
 compute=st.mean(r['gflops'] for r in rows if r['kind']=='compute')
 bands=collections.defaultdict(list)
 for r in rows:
  if r['kind']=='read':bands[r['bytes']].append(r['GBps'])
 bands={k:st.mean(v) for k,v in bands.items()}
 # Bracket the active pair's 153 KiB working set with 128/256 KiB probes.
 bw=st.mean([bands[131072],bands[262144]])
 us=timing['general_silu'+('_avx2' if isa=='avx2' else '')]['mean_us']
 effective=pair['dense_flops']/us/1000
 compute_us=pair['dense_flops']/compute/1000
 bandwidth_us=pair['parameter_bytes']/bw/1000
 result['backends'][isa]={'compute_gflops':compute,'read_GBps_by_bytes':bands,'L2_bracket_GBps':bw,
                         'dense_compute_bound_us':compute_us,'dense_bandwidth_bound_us':bandwidth_us,
                         'dense_lower_bound_us':max(compute_us,bandwidth_us),'inference_us':us,'effective_dense_gflops':effective}
 label='SSE' if isa=='sse' else 'AVX2/FMA'
 ax.loglog(xs,np.minimum(compute,bw*xs),color=color,label=label+' dense roofline')
 ax.scatter(pair['intensity_flop_per_byte'],effective,color=color,s=65,zorder=4)
 ax.annotate(f'{label}: {us:.2f} µs', (pair['intensity_flop_per_byte'],effective),xytext=(12,-6 if isa=='sse' else 3),textcoords='offset points',color=color)
ax.axvline(pair['intensity_flop_per_byte'],color='gray',ls=':',lw=1)
ax.set(xlabel='Dense arithmetic intensity [FLOP / parameter byte]',ylabel='Dense FLOPs / full inference time [GFLOP/s]',title='Two pixel NNs: measured latency versus dense-only bounds',xlim=(.05,4),ylim=(2,220))
ax.grid(alpha=.2,which='both');ax.legend(loc='upper left',fontsize=9)
for suffix in ['png','pdf','svg']:fig.savefig(O/('roofline.'+suffix),dpi=180)
(O/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
