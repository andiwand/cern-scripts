#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/isometry-6040/env6040.sh
cd $ACI_BASE/athena-build-6040
cmake --build . -- -k 0 -j 28 "$@"
