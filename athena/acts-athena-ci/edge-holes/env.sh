#!/bin/bash
# Edge-hole border default: nightly 2026-11-19T2100, worktree athena-edgehole (branch edge-hole-border)
export NIGHTLY_NAME=2026-11-19T2100
source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1
BUILD_SRC=athena-edgehole; BUILD_DIR=athena-build-edgehole   # common/build.sh: ActsConfig only (python)
