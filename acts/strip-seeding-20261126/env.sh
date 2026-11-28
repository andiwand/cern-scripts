#!/bin/bash
export NIGHTLY_NAME=2026-11-16T2100
source /home/astefl/source/acts/acts-athena-ci/env.sh
export STRIP_STUDY=/home/astefl/source/acts/acts-athena-ci/studies/strip-seeding-20261126
if [ -f "$ACI_BASE/athena-build-strip-seeding/x86_64-el9-gcc15-opt/setup.sh" ]; then
  source "$ACI_BASE/athena-build-strip-seeding/x86_64-el9-gcc15-opt/setup.sh"
fi
