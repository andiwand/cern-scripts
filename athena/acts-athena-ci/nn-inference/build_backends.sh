#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-study-build-env.log 2>&1
set -e
command -v g++ >/dev/null
mkdir -p "$NN_STUDY_ROOT/build"
g++ -O2 -DNDEBUG -std=c++23 -fPIC -shared \
 -I"$NN_STUDY_EXTERNALS/include" \
 -I"$ROOTSYS/include" \
 -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" \
 -I"$NN_STUDY_ROOT/models" \
 "$NN_STUDY_SCRIPTS/NNInferenceStudy.cxx" \
 -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -llwtnn \
 -L"$NN_STUDY_LCG/blas/0.3.33/x86_64-el9-gcc15-opt/lib" -lopenblas \
 -o "$NN_STUDY_ROOT/build/libNNInferenceStudy.so"
echo 'Built inference backends'
g++ -O2 -DNDEBUG -std=c++23 "$NN_STUDY_SCRIPTS/bench.cxx" \
 -L"$NN_STUDY_ROOT/build" -lNNInferenceStudy \
 -Wl,-rpath,"$NN_STUDY_ROOT/build" -o "$NN_STUDY_ROOT/build/bench"
echo 'Built standalone benchmark'
