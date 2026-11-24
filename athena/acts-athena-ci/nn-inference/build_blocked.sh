#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-blocked-build-env.log 2>&1
set -e
nn_output="$NN_STUDY_ROOT/build-blocked"
mkdir -p "$nn_output"
python3 - <<'PY'
import os,re,shutil
from pathlib import Path
s=Path(os.environ['NN_STUDY_SCRIPTS']);out=Path(os.environ['NN_STUDY_ROOT'])/'build-blocked'
source=(s/'NNInferenceStudy.cxx').read_text()
k=(s/'kernels.cxx').read_text()
body=k.split('void blockedKernel(',1)[1].split('{',1)[1].split('\n}\n__attribute__((noinline))',1)[0]
body=body.replace('if constexpr(Out<16) { nnstudy::dense<In,Out>(l,x,y); return; }', '''if constexpr(Out<16) {
    std::copy_n(l.bias.data(),Out,y);
    for(unsigned j=0;j<In;++j) for(unsigned i=0;i<Out;++i) y[i]+=x[j]*l.weights[j*Out+i];
    return;
  }''')
start=source.index('void dense(const Layer&')
end=source.index('\ntemplate<unsigned In,unsigned Out>\n__attribute__((target',start)
signature=source[start:source.index('{',start)]
source=source[:start]+signature+'{'+body+'\n}\n'+source[end:]
old='b=="direct" || b=="direct_avx2"'
assert source.count(old)==1
source=source.replace(old,old+' || b=="direct_blocked"')
source='#include <xmmintrin.h>\n'+source
(out/'NNInferenceStudy.cxx').write_text(source)
shutil.copy2(s/'NNInferenceStudy.h',out/'NNInferenceStudy.h')
PY
g++ -O2 -DNDEBUG -std=c++23 -fPIC -shared \
 -I"$NN_STUDY_EXTERNALS/include" -I"$ROOTSYS/include" \
 -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" \
 -I"$NN_STUDY_ROOT/models" "$nn_output/NNInferenceStudy.cxx" \
 -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -llwtnn \
 -L"$NN_STUDY_LCG/blas/0.3.33/x86_64-el9-gcc15-opt/lib" -lopenblas \
 -o "$nn_output/libNNInferenceStudy.so"
g++ -O2 -DNDEBUG -std=c++23 "$NN_STUDY_SCRIPTS/bench.cxx" \
 -L"$nn_output" -lNNInferenceStudy -Wl,-rpath,"$nn_output" -o "$nn_output/bench"
sha256sum "$nn_output/libNNInferenceStudy.so" "$nn_output/NNInferenceStudy.cxx" > "$nn_output/libraries.txt"
