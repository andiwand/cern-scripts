#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-profile-env.log 2>&1
set -e
roof_root=/home/astefl/source/acts/acts-athena-ci
roof_out=$roof_root/run/native-pixel-nn/roofline
roof_opt=$roof_root/run/native-pixel-nn/optimization
roof_pkg=$roof_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
g++ -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 -I"$roof_pkg" -I"$NN_STUDY_EXTERNALS/include" -c /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/bench.cxx -o "$roof_out/bench.o"
for roof_variant in general_silu general_silu_avx2; do
 g++ "$roof_out/bench.o" -L"$roof_opt" -lNative_$roof_variant -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$roof_opt:$NN_STUDY_EXTERNALS/lib" -o "$roof_out/bench_$roof_variant"
done
