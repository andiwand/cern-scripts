#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz2env.sh >/dev/null 2>&1
cd $ACI_BASE/athena-build-rz2
cmake --build . -- -j 32
echo "RZ2BUILD_RC=$?"
