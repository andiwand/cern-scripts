#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/pixel-space-points/pixenv.sh >/dev/null 2>&1
mkdir -p $ACI_BASE/athena-build && cd $ACI_BASE/athena-build
cmake "$ATHENA_SOURCE/Projects/WorkDir" -GNinja \
  -DCMAKE_MAKE_PROGRAM="$(which ninja)" \
  -DATLAS_PACKAGE_FILTER_FILE=$ACI_BASE/package_filters_nogpu.txt \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) \
  -DATLAS_ACTS_SOURCE_DIR=$ACTS_SOURCE \
  -DACTS_ENABLE_CUDA=OFF -DACTS_BUILD_PLUGIN_GNN=OFF \
  -DACTS_BUILD_PLUGIN_TRACCC=OFF -DDETRAY_BUILD_CUDA=OFF
echo "PIXCONFIG_RC=$?"
