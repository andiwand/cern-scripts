#!/usr/bin/env python3
"""Standalone scientific figure, also embedded in the HTML note."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
d=json.loads((R/'summary.json').read_text())
names={'original':'Current ONNX','ort_cached':'Cached ONNX','ort_simple':'Simplified ONNX','direct':'Direct C++ (SSE)','direct_blocked':'Direct C++ (blocked SSE)','direct_avx2':'Direct C++ (AVX2)','sofie':'SOFIE (GEMM)','sofie_gemv':'SOFIE (GEMV)','lwtnn':'LWTNN float','lwtnn_double':'LWTNN double'}
backends=[b for b in names if b in d['isolated'] and '0' in d['isolated'][b]]
complete=all(b in d['integrated'] for b in backends)
fig,axes=plt.subplots(1,2 if complete else 1,figsize=(12 if complete else 7,6.5),squeeze=False)
ax=axes[0,0];y=np.arange(len(backends))
for pressure,offset,color,label in [('0',-.18,'#237ca4','Warm'),('1048576',.18,'#df9953','After 1 MiB cache sweep')]:
    means=[d['isolated'][b].get(pressure,{}).get('mean_us',float('nan')) for b in backends]
    errors=[d['isolated'][b].get(pressure,{}).get('sd_us',0) or 0 for b in backends]
    ax.barh(y+offset,means,height=.32,xerr=errors,color=color,label=label,capsize=2)
ax.set_yticks(y,[names[b] for b in backends]);ax.invert_yaxis();ax.set_xlabel('Two-network inference [μs / calibration]')
ax.set_title('Standalone, real cluster inputs');ax.legend(loc='lower right',fontsize=8);ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
if complete:
    ax=axes[0,1]
    for field,offset,color,label in [('ckf_ms',-.18,'#237ca4','Primary CKF CPU'),('event_ms',.18,'#61a476','Event CPU')]:
        means=[100*d['integrated'][b]['comparisons'][field]['normalized_ratio'] for b in backends]
        errors=[100*(d['integrated'][b]['comparisons'][field]['sd_ratio'] or 0) for b in backends]
        ax.barh(y+offset,means,height=.32,xerr=errors,color=color,label=label,capsize=2)
    ax.set_yticks(y,[names[b] for b in backends]);ax.invert_yaxis();ax.axvline(100,color='#555',ls=':',lw=1)
    ax.set_xlabel('CPU relative to current ONNX [%]');ax.set_title('Serial Athena, normalized to pixel clustering')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2,fontsize=8);ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
fig.suptitle('Pixel NN inference backends — 2026-11-24',fontsize=15)
fig.text(.5,.012,'Error bars: scatter between alternating cycles. Cache sweep is synthetic.\nBackground-load limits are documented in the note.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.08,1,.95))
out=R/'plots';out.mkdir(exist_ok=True)
for ext in ['png','pdf','svg']:fig.savefig(out/f'latency-comparison.{ext}',dpi=160)
print(out)
