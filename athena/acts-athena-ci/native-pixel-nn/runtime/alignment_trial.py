#!/usr/bin/env python3
"""Short compute-only storage alignment trial; never edits Athena sources."""
import json, os, shutil, statistics, subprocess
from pathlib import Path
root = Path('/home/astefl/source/acts/acts-athena-ci')
pkg = root/'athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool'
out = root/'run/native-pixel-nn/mr-review/alignment'
out.mkdir(exist_ok=True)
external = Path(os.environ['NN_STUDY_EXTERNALS'])
lcg = Path(os.environ['NN_STUDY_LCG'])
inputs = root/'run/nn-inference/captured-inputs.bin'
bench = Path(__file__).with_name('bench.cxx')
sources = ['NativePixelClusterNN', 'NativePixelClusterNNBaseline', 'NativePixelClusterNNAvx2']
variants = ['plain', 'align32', 'align64']
for variant in variants:
    source = out/variant/'source'
    shutil.copytree(pkg/'SiClusterizationTool', source/'SiClusterizationTool', dirs_exist_ok=True)
    shutil.copytree(pkg/'src', source/'src', dirs_exist_ok=True)
    if variant != 'plain':
        alignment = int(variant.removeprefix('align'))
        path = source/'SiClusterizationTool/NativePixelClusterNN.h'
        text = path.read_text().replace('#include <vector>', '#include "CxxUtils/aligned_vector.h"')
        text = text.replace('std::vector<float>', f'CxxUtils::aligned_vector<float, {alignment}>')
        path.write_text(text)
        path = source/'src/NativePixelClusterNN.cxx'
        text = path.read_text().replace('layer.bias = std::move(capture.tensors[2 * i + 1]);',
            'layer.bias.assign(capture.tensors[2 * i + 1].begin(), capture.tensors[2 * i + 1].end());')
        path.write_text(text)
    for compiler, cxx in [('gcc','g++'), ('clang','/usr/bin/clang++')]:
        directory = out/variant/compiler
        directory.mkdir(exist_ok=True)
        flags = ['-O2', '-DNDEBUG', '-std=c++23', '-fPIC', '-march=x86-64-v2',
            '-I'+str(source), '-I'+str(external/'include'),
            '-I'+str(root/'athena-native-pixel-nn/Control/CxxUtils'),
            '-I'+str(lcg/'eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3'),
            '-I'+str(lcg/'Boost/1.91.0/x86_64-el9-gcc15-opt/include')]
        with (directory/'build.log').open('w') as log:
            objects = []
            for name in sources:
                extra = ['-DSICLUSTERIZATION_NATIVE_NN_HAVE_AVX2']
                if name.endswith(('Baseline','Avx2')):
                    extra += ['-fvisibility=hidden', '-fvisibility-inlines-hidden',
                              '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))']
                if name.endswith('Avx2'): extra += ['-mavx2','-mfma','-DEIGEN_MAX_ALIGN_BYTES=16']
                obj = directory/(name+'.o'); objects.append(str(obj))
                subprocess.run([cxx,*flags,*extra,'-c',str(source/'src'/(name+'.cxx')),'-o',str(obj)],
                               check=True,stdout=log,stderr=log)
            subprocess.run([cxx,'-shared',*objects,'-L'+str(external/'lib'),'-lonnxruntime',
                '-Wl,-rpath,'+str(external/'lib'),'-o',str(directory/'libAlignment.so')],check=True,stdout=log,stderr=log)
            subprocess.run([cxx,*flags,str(bench),'-L'+str(directory),'-lAlignment',
                '-L'+str(external/'lib'),'-lonnxruntime','-Wl,-rpath,'+str(directory)+':'+str(external/'lib'),
                '-o',str(directory/'bench')],check=True,stdout=log,stderr=log)
rows=[]
with (out/'timing.jsonl').open('w') as log:
    for cycle in range(3):
        for compiler in ('gcc','clang'):
            for mode in ('auto','sse'):
                for variant in (variants if cycle%2==0 else variants[::-1]):
                    directory=out/variant/compiler
                    env=os.environ.copy();env['NATIVE_NN_REPEATS']='3'
                    env.pop('NATIVE_NN_FORCE_SSE',None)
                    if mode=='sse':env['NATIVE_NN_FORCE_SSE']='1'
                    binary=directory/'bench'
                    if cycle==0:
                        dump=directory/(mode+'.bin')
                        subprocess.run([str(binary),'dump',str(inputs),'10000',str(dump)],env=env,check=True)
                        assert dump.read_bytes()==(out/'plain'/compiler/(mode+'.bin')).read_bytes()
                    result=subprocess.check_output(['taskset','-c','16',str(binary),'time',str(inputs),'50000','unused'],env=env,text=True)
                    row=dict(variant=variant,compiler=compiler,mode=mode,cycle=cycle+1,**json.loads(result))
                    rows.append(row);log.write(json.dumps(row)+'\n');log.flush()
        print('cycle',cycle+1,flush=True)
summary={}
for compiler in ('gcc','clang'):
    summary[compiler]={}
    for mode in ('auto','sse'):
        summary[compiler][mode]={}
        baseline=[r['us'] for r in rows if (r['compiler'],r['mode'],r['variant'])==(compiler,mode,'plain')]
        for variant in variants:
            values=[r['us'] for r in rows if (r['compiler'],r['mode'],r['variant'])==(compiler,mode,variant)]
            summary[compiler][mode][variant]=dict(mean_us=statistics.mean(values),sd_us=statistics.stdev(values),
                paired_change_percent=statistics.mean(100*(v/b-1) for v,b in zip(values,baseline)))
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
