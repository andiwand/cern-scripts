#!/bin/bash
# Study env for ../common/idpvm.sh: the scattering-tail nightly; IDPVM over the pilot AODs.
# The study build (athena-build-tail-score) is not made with common/build.sh.
source ~/scripts/athena/acts-athena-ci/scattering-tail/env.sh
unset BUILD_SRC BUILD_DIR BUILD_ARGS
IDPVM_RUNS=pilot
