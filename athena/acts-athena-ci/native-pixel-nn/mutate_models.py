#!/usr/bin/env python3
"""Generate changed-model acceptance/rejection fixtures for validate_layout.sh.

mutate_models.py [OUT] [--source MODEL_DIR]
Writes OUT/CASE/{number,pos1,pos2,pos3}.onnx. Accepted: weights, metadata, extra.
Rejected: nonfinite, normalization, activation, shape, missing, dtype, precision,
output_order. ONNX (Python) is an offline test dependency only.
"""
import argparse
from pathlib import Path
import numpy as np
import onnx
from onnx import numpy_helper
parser=argparse.ArgumentParser()
parser.add_argument('out',nargs='?',type=Path,default=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/mutations'))
parser.add_argument('--source',type=Path,default=Path('/cvmfs/atlas.cern.ch/repo/sw/database/GroupData/ITkPixelClusterization/nn-01-01-01'))
args=parser.parse_args()
source=args.source
root=args.out
for case in ['weights','nonfinite','normalization','activation','shape','extra','missing','dtype','metadata','precision','output_order']:
    folder=root/case
    folder.mkdir(parents=True,exist_ok=True)
    for name in ['number','pos1','pos2','pos3']:
        model=onnx.load(source/f'{name}.onnx')
        if case=='weights':
            for t in model.graph.initializer:
                values=numpy_helper.to_array(t).copy()
                values += np.float32(0.001)
                t.CopyFrom(numpy_helper.from_array(values,t.name))
        elif case=='metadata':
            model.producer_name='native-review'
            model.producer_version='metadata-only'
            model.doc_string='Re-exported with identical computation'
            model.graph.name='renamed-graph'
            model.model_version=42
            values=list(model.graph.initializer)
            del model.graph.initializer[:]
            model.graph.initializer.extend(reversed(values))
        elif case=='precision':
            if name=='number':
                onnx.save(model,folder/f'{name}.onnx');continue
            found=False
            for n in model.graph.node:
                for a in n.attribute:
                    if a.HasField('t') and a.t.data_type == onnx.TensorProto.FLOAT:
                        v=numpy_helper.to_array(a.t).copy()
                        if np.any(v==np.float32(1e-4)):
                            v[v==np.float32(1e-4)]=np.float32(.01)
                            a.t.CopyFrom(numpy_helper.from_array(v,a.t.name));found=True
            assert found
        elif case=='output_order':
            output=model.graph.output[0].name
            before='review_before_permutation'
            for node in model.graph.node:
                for i,value in enumerate(node.output):
                    if value==output:node.output[i]=before
            n=3 if name=='number' else 5*int(name[-1])
            perm=np.arange(n,dtype=np.int64);perm[0],perm[1]=perm[1],perm[0]
            model.graph.initializer.append(numpy_helper.from_array(perm,'review_permutation'))
            model.graph.node.append(onnx.helper.make_node('Gather',[before,'review_permutation'],[output],axis=1))
        elif case=='nonfinite':
            t=model.graph.initializer[0]; values=numpy_helper.to_array(t).copy()
            values.flat[0]=np.nan;t.CopyFrom(numpy_helper.from_array(values,t.name))
        elif case=='normalization':
            found=False
            for n in model.graph.node:
                for a in n.attribute:
                    if a.HasField('t') and a.t.data_type == onnx.TensorProto.FLOAT:
                        v=numpy_helper.to_array(a.t).copy()
                        if np.any(v==np.float32(1e-5)):
                            v[v==np.float32(1e-5)]=np.float32(2e-5)
                            a.t.CopyFrom(numpy_helper.from_array(v,a.t.name));found=True
            assert found
        elif case=='activation':
            next(n for n in model.graph.node if n.op_type=='Sigmoid').op_type='Softmax'
        elif case=='shape':
            model.graph.initializer[0].dims[1]=66
        elif case=='extra':
            model.graph.initializer.append(numpy_helper.from_array(np.array([1.],dtype=np.float32),'unsupported-extra'))
        elif case=='missing':
            del model.graph.initializer[0]
        elif case=='dtype':
            t=model.graph.initializer[0]; t.CopyFrom(numpy_helper.from_array(numpy_helper.to_array(t).astype(np.float64),t.name))
        onnx.save(model,folder/f'{name}.onnx')
