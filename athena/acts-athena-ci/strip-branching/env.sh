#!/bin/bash
# Strip-entry branching: nightly 2026-11-19T2100, worktree athena-branching (branch strip-entry-branching)
export NIGHTLY_NAME=2026-11-19T2100
source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1
BUILD_SRC=athena-branching; BUILD_DIR=athena-build-branching   # common/build.sh: ActsTrackReconstruction
