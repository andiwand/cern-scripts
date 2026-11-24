#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/env.sh > /tmp/native-pixel-tests-env.log 2>&1
set -e
cd /home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn
source x86_64-el9-gcc15-opt/setup.sh >> /tmp/native-pixel-tests-env.log 2>&1
ctest --output-on-failure -R 'SiClusterizationTool_NativePixelClusterNN|ActsConfig_ActsPixelNNInferenceConfig|ActsTrackReconstruction_' > tests.log 2>&1
cat tests.log
