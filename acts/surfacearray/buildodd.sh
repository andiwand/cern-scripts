#!/bin/bash
set -e
SRC=/Users/andreas/cern/source/acts/acts/dev3
BLD=/Users/andreas/cern/build/acts/acts/dev3
DEPS=/Users/andreas/cern/source/acts/ci-dependencies/.spack-env
INC="-I$SRC/Core/include -I$BLD/Core/include"
INC="$INC -I$SRC/Fatras/include"
for d in $SRC/Examples/Detectors/*/include $SRC/Examples/Framework/include $SRC/Plugins/DD4hep/include $SRC/Plugins/Root/include $SRC/Plugins/FpeMonitoring/include $SRC/Plugins/Json/include; do INC="$INC -I$d"; done
/usr/bin/clang++ -std=gnu++20 -O1 -g -DNDEBUG $INC \
  -isystem $SRC/cmake/assert_include \
  -isystem $DEPS/._view/g65lbzilk6lk6puo4v5oxacyktlt3js5/include \
  -isystem $DEPS/view/include/root -isystem $DEPS/view/include \
  -isystem $DEPS/view/include/eigen3 \
  -arch arm64 -isysroot /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
  "$1" -o "${1%.cpp}" \
  -L$BLD/lib -L$BLD/Examples/Detectors/DD4hepDetector -L$DEPS/view/lib -L$DEPS/view/lib/root \
  -lActsCore -lActsExamplesDetectorDD4hep -lActsExamplesDetectorsCommon -lActsExamplesFramework -lActsPluginDD4hep -lCore -lRIO -lMathCore -lGeom \
  -Wl,-rpath,$BLD/lib -Wl,-rpath,$BLD/Examples/Detectors/DD4hepDetector -Wl,-rpath,$DEPS/view/lib -Wl,-rpath,$DEPS/view/lib/root
