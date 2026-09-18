#!/bin/bash
# Run environment for the RZ track finder (v47.7.0 trees): rz2env.sh plus the build's setup.sh
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz2env.sh >/dev/null 2>&1
source $ACI_BASE/athena-build-rz2/${LCG_PLATFORM}/setup.sh
