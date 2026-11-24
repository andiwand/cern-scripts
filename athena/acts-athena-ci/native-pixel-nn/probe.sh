#!/bin/bash
set -eo pipefail
cd /home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > env.log 2>&1
set -e
g++ -O2 -std=c++23 /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/fingerprint_probe.cxx -I"$NN_STUDY_EXTERNALS/include" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o probe
for native_name in number pos1 pos2 pos3; do
 for native_repeat in 1 2 3; do
 ./probe /cvmfs/atlas.cern.ch/repo/sw/database/GroupData/ITkPixelClusterization/nn-01-01-01/$native_name.onnx $native_name.$native_repeat.graph
 done
done
sha256sum *.graph
