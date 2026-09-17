#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/pixel-space-points/pixenv.sh >/dev/null 2>&1
cd $ACI_BASE/athena-build
nice -n 5 cmake --build . -- -j 32 -k 0
echo "PIXBUILD_RC=$?"
