#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/gbts/gbtsenv.sh >/dev/null 2>&1
cd $GBTS_BUILD
nice -n 5 cmake --build . -- -j 32 -k 0
echo "GBTSBUILD_RC=$?"
