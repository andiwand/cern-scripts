#!/bin/bash
source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1
cd $ACI_BASE/athena-build      && nice -n 5 cmake --build . -- -j 28 -k 0; echo "BUILD_PR_RC=$?"
cd $ACI_BASE/athena-build-base && nice -n 5 cmake --build . -- -j 28 -k 0; echo "BUILD_BASE_RC=$?"
echo "BUILD_GBTS_DONE"
