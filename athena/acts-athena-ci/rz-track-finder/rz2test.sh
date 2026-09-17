#!/bin/bash
# Build and run the RZ unit tests of acts-rz2 in the release's environment
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz2env.sh >/dev/null 2>&1
BUILD=/home/astefl/source/acts/acts-athena-ci/acts-rz2-unittest-build
BOOST=$(ls -d /cvmfs/atlas-nightlies.cern.ch/repo/sw/main_Athena_x86_64-el9-gcc15-opt/sw/lcg/releases/Boost/*/x86_64-el9-gcc15-opt/lib/cmake/Boost-* | tail -1)
cmake -S $ACTS_SOURCE -B $BUILD -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) \
  -DACTS_BUILD_UNITTESTS=ON -DBoost_DIR=$BOOST \
  -DACTS_BUILD_EXAMPLES=OFF -DACTS_BUILD_PLUGIN_GNN=OFF \
  -DACTS_BUILD_PLUGIN_TRACCC=OFF -DACTS_ENABLE_CUDA=OFF > $BUILD.cfg.log 2>&1
echo "CFG_RC=$?"
cmake --build $BUILD --target ActsUnitTestRzTransport ActsUnitTestRzMeasurementGrid ActsUnitTestRzTrackFinder -- -j 16 > $BUILD.build.log 2>&1
echo "BUILD_RC=$?"
for t in RzTransport RzMeasurementGrid RzTrackFinder; do
  $BUILD/bin/ActsUnitTest$t 2>&1 | tail -2
done
