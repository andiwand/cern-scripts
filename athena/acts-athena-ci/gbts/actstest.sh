#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/gbts/gbtsenv.sh >/dev/null 2>&1
BUILD=/home/astefl/source/acts/acts-athena-ci/acts-unittest-build
cmake -S $ACTS_SOURCE -B $BUILD -GNinja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) \
  -DACTS_BUILD_UNITTESTS=ON \
  -DBoost_DIR=/cvmfs/atlas-nightlies.cern.ch/repo/sw/main_Athena_x86_64-el9-gcc15-opt/sw/lcg/releases/Boost/1.91.0-70248/x86_64-el9-gcc15-opt/lib/cmake/Boost-1.91.0 \
  -DACTS_BUILD_EXAMPLES=OFF -DACTS_BUILD_PLUGIN_GNN=OFF \
  -DACTS_BUILD_PLUGIN_TRACCC=OFF -DACTS_ENABLE_CUDA=OFF > /tmp/claude-148632/-home-astefl-source-acts-acts-athena-ci/d46688de-c657-46dd-80fd-9f666c2c12f6/scratchpad/acts_cfg.log 2>&1
echo "CFG_RC=$?"
cmake --build $BUILD --target ActsUnitTestGbtsSeeding -- -j 32
echo "BUILD_RC=$?"
