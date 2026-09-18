#!/bin/bash

source /home/astefl/scripts/athena/acts-athena-ci/isometry-6040/env6040.sh
mkdir -p $ACI_BASE/athena-build-6040
cd $ACI_BASE/athena-build-6040
cmake "$ATHENA_SOURCE/Projects/WorkDir" -GNinja \
  -DCMAKE_MAKE_PROGRAM="$(which ninja)" \
  -DATLAS_PACKAGE_FILTER_FILE=/home/astefl/scripts/athena/acts-athena-ci/isometry-6040/package_filters_6040.txt \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) \
  -DATLAS_ACTS_SOURCE_DIR=$ACTS_SOURCE \
  -DACTS_ENABLE_CUDA=OFF -DACTS_BUILD_PLUGIN_GNN=OFF \
  -DACTS_BUILD_PLUGIN_TRACCC=OFF -DDETRAY_BUILD_CUDA=OFF
