#!/usr/bin/env python3
"""Summarize all-model output comparisons; retain every backend's raw outputs."""
import argparse,json
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser();p.add_argument('directory',type=Path);args=p.parse_args()
reference=np.fromfile(args.directory/'original.bin',dtype='<f4').reshape(-1,33)
result={'inputs':len(reference),'reference':'original ONNX, all four models','backends':{}}
for path in sorted(args.directory.glob('*.bin')):
    if path.name=='original.bin':continue
    value=np.fromfile(path,dtype='<f4').reshape(-1,33)
    assert value.shape==reference.shape
    delta=np.abs(value.astype(float)-reference)
    finite=np.isfinite(value).all()
    r={'finite':bool(finite),'max_abs':float(delta.max()),'max_scaled':float((delta/(1+np.abs(reference))).max()),
       'argmax_changes':int(np.count_nonzero(value[:,:3].argmax(1)!=reference[:,:3].argmax(1))),
       'abs_quantiles':np.quantile(delta,[.5,.9,.99,.999,1]).tolist(),'networks':{}}
    offset=0
    for name,n in [('number',3),('pos1',5),('pos2',10),('pos3',15)]:
        d=delta[:,offset:offset+n];ref=reference[:,offset:offset+n]
        r['networks'][name]={'max_abs':float(d.max()),'max_scaled':float((d/(1+np.abs(ref))).max()),
                            'rms':float(np.sqrt(np.mean(d*d)))}
        offset+=n
    # A diagnostic tolerance, not the physics-equivalence criterion.
    r['elements_outside_1e-5_plus_1e-4_relative']=int(np.count_nonzero(delta>1e-5+1e-4*np.abs(reference)))
    # Near-zero precision outputs make a global absolute tolerance insufficient.
    # Check all heads, and separately only the model selected by multiplicity.
    all_relative=[];selected_relative=[]
    selected=reference[:,:3].argmax(1)+1
    for n,offset in [(1,3),(2,8),(3,18)]:
        cols=[offset+5*j+k for j in range(n) for k in [3,4]]
        ref_precision=reference[:,cols]
        assert np.all(ref_precision>0)
        relative=delta[:,cols]/ref_precision
        all_relative.extend(relative.flatten())
        selected_relative.extend(relative[selected==n].flatten())
    r['max_relative_precision_error_all_heads']=float(np.max(all_relative))
    r['max_relative_precision_error_selected_model']=float(np.max(selected_relative))
    result['backends'][path.stem]=r
(args.directory/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert all(r['finite'] for r in result['backends'].values())
