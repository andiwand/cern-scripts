#!/bin/bash
# Configure both GBTS measurement builds: PR (acts/) and baseline (acts-base/),
# without the CUDA/GNN/traccc plugins - no filtered package links them.
source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1
cfg () {  # cfg <build dir> <acts source>
  mkdir -p $1; cd $1
  cmake "$ATHENA_SOURCE/Projects/WorkDir" -GNinja \
    -DCMAKE_MAKE_PROGRAM="$(which ninja)" \
    -DATLAS_PACKAGE_FILTER_FILE=$ACI_BASE/package_filters_nogpu.txt \
    -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) \
    -DATLAS_ACTS_SOURCE_DIR=$2 \
    -DACTS_ENABLE_CUDA=OFF -DACTS_BUILD_PLUGIN_GNN=OFF \
    -DACTS_BUILD_PLUGIN_TRACCC=OFF -DDETRAY_BUILD_CUDA=OFF
  echo "CONFIG_RC_$1=$?"
  cd $ACI_BASE
}
cfg $ACI_BASE/athena-build      $ACI_BASE/acts
cfg $ACI_BASE/athena-build-base $ACI_BASE/acts-base
echo "CONFIG_GBTS_DONE"
