#!/usr/bin/env bash
set -eo pipefail
variant=$1
base=${ACTS_EDM_EXPERIMENT_ROOT:-/private/tmp/acts-edm-2026-10-31}
edm_view=/Users/andreas/cern/source/acts/ci-dependencies/.spack-env/view
export ROOTSYS=$("$edm_view/bin/root-config" --prefix)
export DYLD_LIBRARY_PATH="$ROOTSYS/lib/root:$edm_view/lib"
export DD4HEP_LIBRARY_PATH="$edm_view/lib"
export DD4hepINSTALL="$edm_view"
. "$base/build-$variant/this_acts.sh" >/dev/null
ctest --test-dir "$base/build-$variant" --output-on-failure -j 4 -R '^(MultiTrajectory|Track|AnyTrackProxy|AnyTrackStateProxy|AnyTrackContainer|TrackStatePropMask|MultiTrajectoryHelpers|TrackParameterHelpers|MeasurementSelector|CombinatorialKalmanFilter|TrackSelector|GainMatrixSmoother|GainMatrixUpdater|KalmanFitter|Gsf|GsfComponentMerging|GsfMixtureReduction|MbfSmoother|ReferenceTrajectoryBuilder|TrackHelpers|Gx2f|MeasurementResidual)$'
