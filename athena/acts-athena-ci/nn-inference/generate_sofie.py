#!/usr/bin/env python3
import os
import json
from pathlib import Path
import ROOT

root=Path(os.environ['NN_STUDY_ROOT'])
os.chdir(root/'models')
patches=[]
for name in ['number','pos1','pos2','pos3']:
    parser=ROOT.TMVA.Experimental.SOFIE.RModelParser_ONNX()
    model=parser.Parse(name+'_simple.onnx')
    model.Generate()
    model.OutputGenerated(name+'_sofie.hxx')
    header=Path(name+'_sofie.hxx')
    text=header.read_text()
    # ROOT 6.40.02's non-last-axis Softmax generator omits this semicolon.
    bad='size_t id = index + i      tensor_probabilities[id] /= sum;'
    if bad in text:
        assert text.count(bad)==1
        header.write_text(text.replace(bad,'size_t id = index + i;\n      tensor_probabilities[id] /= sum;'))
        patches.append({'header':str(header),'fix':'Missing semicolon in generated non-last-axis Softmax; no arithmetic change'})
    text=header.read_text()
    # The generated, normally unused GEMV declaration incorrectly marks Y const.
    bad_y='const float * beta, const float * Y'
    if bad_y in text:
        text=text.replace(bad_y,'const float * beta, float * Y')
        header.write_text(text)
        patches.append({'header':str(header),'fix':'Correct GEMV output pointer declaration from const float* to float*'})
    for i in range(3):
        old=f'1 / (1 + std::exp( - tensor_dense{i}[id]))'
        assert text.count(old)==1
        text=text.replace(old,f'nnstudy::sigmoid(tensor_dense{i}[id])')
    header.write_text(text)
    patches.append({'header':str(header),'fix':'Stable sigmoid avoids exponential overflow for large negative activations'})
    specialized=text.replace('ROOT_TMVA_SOFIE_'+name.upper()+'_SIMPLE','ROOT_TMVA_SOFIE_'+name.upper()+'_SIMPLE_GEMV')
    specialized=specialized.replace('TMVA_SOFIE_'+name+'_simple','TMVA_SOFIE_'+name+'_simple_gemv')
    assert specialized.count('TMVA::Experimental::SOFIE::Gemm_Call(')==5
    specialized=specialized.replace('TMVA::Experimental::SOFIE::Gemm_Call(','nnstudy::gemvCall(')
    Path(name+'_sofie_gemv.hxx').write_text(specialized)
    print('GENERATED',name,flush=True)
(root/'sofie-generation-fixes.json').write_text(json.dumps(patches,indent=2)+'\n')
