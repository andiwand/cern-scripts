#!/bin/bash
source /home/astefl/source/acts/acts-athena-ci/studies/strip-seeding-20261126/env.sh > env.log 2>&1
exec python "$STRIP_STUDY/run.py" "$@" > run.log 2>&1
