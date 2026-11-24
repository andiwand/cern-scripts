#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
d=json.loads((R/'kernel-summary.json').read_text());rows=d['rows'];y=np.arange(len(rows))
fig,ax=plt.subplots(figsize=(8,4.8))
for field,offset,color,label in [('sse',-.24,'#777d85','Direct SSE'),('gemv',0,'#237ca4','OpenBLAS GEMV'),('sse_blocked',.24,'#39966a','Blocked SSE')]:
    ax.barh(y+offset,[r[field] for r in rows],height=.21,color=color,label=label)
ax.set_yticks(y,[r['shape'] for r in rows]);ax.invert_yaxis()
ax.set_xlabel('Dense-layer time summed over number + pos1 [μs]')
ax.set_title('The direct SSE gap is mainly in the 128 → 64 layer')
ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='lower right',fontsize=9)
fig.text(.5,.02,'Diagnostic: layers warmed separately; loop baseline subtracted.\nBlocking preserves the input accumulation order.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.09,1,1));out=R/'plots';out.mkdir(exist_ok=True)
for ext in ['png','pdf','svg']:fig.savefig(out/f'kernel-comparison.{ext}',dpi=160)
