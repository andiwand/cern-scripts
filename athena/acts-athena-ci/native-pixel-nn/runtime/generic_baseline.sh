#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-generic-baseline-env.log 2>&1
source /home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh >> /tmp/native-generic-baseline-env.log 2>&1
set -euo pipefail
generic_root=/home/astefl/source/acts/acts-athena-ci
generic_out=$generic_root/run/native-pixel-nn/generic/baseline
g++ -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 -I"$generic_out" -I"$NN_STUDY_EXTERNALS/include" -I"$generic_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/Boost/1.91.0/x86_64-el9-gcc15-opt/include" /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/runtime/bench.cxx -L"$generic_out" -lSiClusterizationToolLib -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$generic_out:$NN_STUDY_EXTERNALS/lib" -o "$generic_out/bench_gcc"
