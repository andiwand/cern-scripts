#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/gbts/gbtsenv.sh >/dev/null 2>&1
cd $ACI_BASE/athena-build-pin
nice -n 5 cmake --build . -- -j 16 -k 0
echo "PINBUILD_RC=$?"
