#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-v2-build-env.log 2>&1
set -e
nn_output="$NN_STUDY_ROOT/build-x86-v2"
mkdir -p "$nn_output"
g++ -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 -fPIC -shared \
 -I"$NN_STUDY_EXTERNALS/include" -I"$ROOTSYS/include" \
 -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" \
 -I"$NN_STUDY_ROOT/models" "$NN_STUDY_SCRIPTS/NNInferenceStudy.cxx" \
 -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -llwtnn \
 -L"$NN_STUDY_LCG/blas/0.3.33/x86_64-el9-gcc15-opt/lib" -lopenblas \
 -o "$nn_output/libNNInferenceStudy.so"
g++ -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 "$NN_STUDY_SCRIPTS/bench.cxx" \
 -L"$nn_output" -lNNInferenceStudy -Wl,-rpath,"$nn_output" -o "$nn_output/bench"
g++ -march=x86-64-v2 -dM -E -x c++ /dev/null > "$nn_output/compiler-predefines.txt"
sha256sum "$nn_output/libNNInferenceStudy.so" "$nn_output/bench" > "$nn_output/libraries.txt"
g++ -O2 -DNDEBUG -std=c++23 \
 -I"$NN_STUDY_EXTERNALS/include" -I"$ROOTSYS/include" \
 -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" \
 -I"$NN_STUDY_ROOT/models" "$NN_STUDY_SCRIPTS/kernels.cxx" \
 -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -llwtnn \
 -L"$NN_STUDY_LCG/blas/0.3.33/x86_64-el9-gcc15-opt/lib" -lopenblas \
 -o "$NN_STUDY_ROOT/vectorization/kernels"
