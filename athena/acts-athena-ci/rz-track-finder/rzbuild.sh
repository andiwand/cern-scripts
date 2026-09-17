#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzenv.sh >/dev/null 2>&1
cd $ACI_BASE/athena-build-rz
cmake --build . -- -j 32
echo "RZBUILD_RC=$?"
