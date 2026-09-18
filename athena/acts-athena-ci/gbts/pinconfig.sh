#!/bin/bash
# Configure a build of the Acts packages against the nightly's own ACTS
# (no ATLAS_ACTS_SOURCE_DIR), to check what compiles against today's pin.
source /home/astefl/scripts/athena/acts-athena-ci/gbts/gbtsenv.sh >/dev/null 2>&1
PIN_BUILD=$ACI_BASE/athena-build-pin
mkdir -p $PIN_BUILD && cd $PIN_BUILD
cmake "$ATHENA_SOURCE/Projects/WorkDir" -GNinja \
  -DCMAKE_MAKE_PROGRAM="$(which ninja)" \
  -DATLAS_PACKAGE_FILTER_FILE=/home/astefl/scripts/athena/acts-athena-ci/gbts/package_filters_gbts_pin.txt \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache)
echo "PINCONFIG_RC=$?"
