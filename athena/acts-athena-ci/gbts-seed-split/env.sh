#!/bin/bash
# GBTS seed split A/B: nightly 2026-11-16T2100 (ACTS v48.5.0) + athena-gbtssplit (split knobs on GbtsSeedingTool)
export NIGHTLY_NAME=2026-11-16T2100
source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1
BUILD_SRC=athena-gbtssplit; BUILD_DIR=athena-build-gbtssplit   # common/build.sh: ActsPatternRecognition
