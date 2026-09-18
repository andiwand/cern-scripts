#!/bin/bash
# Run environment for the RZ track finder: rzenv.sh plus the build's setup.sh
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzenv.sh >/dev/null 2>&1
source $ACI_BASE/athena-build-rz/${LCG_PLATFORM}/setup.sh
