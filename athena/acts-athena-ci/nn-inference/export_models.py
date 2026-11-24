#!/usr/bin/env python3
"""Export the deployed dense networks without retraining or changing weights."""
from pathlib import Path
import collections
import hashlib
import json
import struct
import numpy as np
import onnx
from onnx import helper as h, numpy_helper as nh, TensorProto as T

root = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
out = root / 'models'
out.mkdir(parents=True, exist_ok=True)
source = Path('/cvmfs/atlas.cern.ch/repo/sw/database/GroupData/ITkPixelClusterization/nn-01-01-01')
manifest = {}
for which, name in enumerate(['number', 'pos1', 'pos2', 'pos3']):
    path = source / (name + '.onnx')
    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    init = {v.name: nh.to_array(v) for v in model.graph.initializer}
    gems = [n for n in model.graph.node if n.op_type == 'Gemm']
    dims = [67, 128, 64, 32, 16, 3 if which == 0 else 5 * which]
    layers = []
    binary = bytearray(struct.pack('<8sI', b'NNSTUDY1', which))
    for i, node in enumerate(gems):
        attrs = {a.name: h.get_attribute_value(a) for a in node.attribute}
        assert attrs == {'alpha': 1., 'beta': 1., 'transB': 1}
        w, b = [init[x] for x in node.input[1:]]
        assert w.shape == (dims[i+1], dims[i]) and b.shape == (dims[i+1],)
        assert w.dtype == np.float32 and b.dtype == np.float32
        binary += struct.pack('<II', dims[i], dims[i+1]) + w.astype('<f4').tobytes() + b.astype('<f4').tobytes()
        layers.append({'architecture': 'dense', 'weights': w.flatten().tolist(), 'bias': b.tolist(),
                       'activation': {'function': 'swish', 'alpha': 1.} if i < 3 else 'linear'})
    (out / (name + '.bin')).write_bytes(binary)
    (out / (name + '.json')).write_text(json.dumps({'inputs': [{'name': f'x{i}', 'offset': 0., 'scale': 1.} for i in range(67)], 'layers': layers, 'outputs': [f'y{i}' for i in range(dims[-1])]}))
    # Preserve floating-point normalization as its own multiplication, not folded
    # into weights. The original seven slices concatenate back in input order.
    constants = {n.output[0]: nh.to_array(h.get_attribute_value(n.attribute[0])) for n in model.graph.node if n.op_type == 'Constant'}
    slices = [n for n in model.graph.node if n.op_type == 'Slice'][:7]
    assert [(int(constants[n.input[1]][0]), int(constants[n.input[2]][0])) for n in slices] == [(0,49),(49,56),(56,63),(63,64),(64,65),(65,66),(66,67)]
    nodes, tensors = [], []
    scale = np.ones((1,67),dtype=np.float32); scale[:,:49] = np.float32(1e-5)
    tensors.append(nh.from_array(scale, 'input_scale'))
    nodes.append(h.make_node('Mul',['NNinputs','input_scale'],['scaled']))
    last = 'scaled'
    for i, node in enumerate(gems):
        for label, original in zip(['w','b'],node.input[1:]):
            tensors.append(nh.from_array(init[original],f'{label}{i}'))
        linear = f'dense{i}'
        nodes.append(h.make_node('Gemm',[last,f'w{i}',f'b{i}'],[linear],transB=1))
        last = linear
        if i < 3:
            nodes += [h.make_node('Sigmoid',[linear],[f'sig{i}']), h.make_node('Mul',[linear,f'sig{i}'],[f'act{i}'])]
            last = f'act{i}'
    if which == 0:
        nodes.append(h.make_node('Softmax',[last],['NN_output'],axis=1))
    else:
        def tensor(name, values, dtype=np.int64):
            tensors.append(nh.from_array(np.asarray(values,dtype=dtype),name))
            return name
        nodes += [h.make_node('Reshape',[last,tensor('head_shape',[which,5])],['head']),
                  h.make_node('Gather',['head',tensor('prob_columns',[0])],['logits'],axis=1),
                  h.make_node('Softmax',['logits'],['probabilities'],axis=0),
                  h.make_node('Gather',['head',tensor('position_columns',[1,2])],['positions'],axis=1),
                  h.make_node('Gather',['head',tensor('precision_columns',[3,4])],['raw_precision'],axis=1),
                  h.make_node('Abs',['raw_precision'],['abs_precision']),
                  h.make_node('Add',['abs_precision',tensor('epsilon',[1e-4],np.float32)],['positive_precision']),
                  h.make_node('Mul',['positive_precision','positive_precision'],['precision']),
                  h.make_node('Concat',['probabilities','positions','precision'],['joined'],axis=1),
                  h.make_node('Reshape',['joined',tensor('output_shape',[1,5*which])],['NN_output'])]
    graph = h.make_graph(nodes,name,[h.make_tensor_value_info('NNinputs',T.FLOAT,[1,67])],[h.make_tensor_value_info('NN_output',T.FLOAT,[1,dims[-1]])],tensors)
    simple = h.make_model(graph,opset_imports=[h.make_opsetid('',17)],ir_version=model.ir_version)
    onnx.checker.check_model(simple)
    onnx.save(onnx.shape_inference.infer_shapes(simple),str(out/(name+'_simple.onnx')))
    (out/(name+'.onnx')).write_bytes(path.read_bytes())
    manifest[name] = {'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dimensions':dims,
                      'parameters':sum(x.size for x in init.values()),'dense_flops':2*sum(a*b for a,b in zip(dims,dims[1:])),
                      'original_nodes':dict(collections.Counter(n.op_type for n in model.graph.node)),
                      'simplified_nodes':dict(collections.Counter(n.op_type for n in simple.graph.node))}
(root/'model-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
