#!/usr/bin/env bash
export NIGHTLY_NAME=2026-11-23T2100
export NN_STUDY_ROOT=/home/astefl/source/acts/acts-athena-ci/run/nn-inference
export NN_STUDY_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/nn-inference
source /home/astefl/source/acts/acts-athena-ci/env.sh
export NN_STUDY_EXTERNALS=/cvmfs/atlas-nightlies.cern.ch/repo/sw/main_Athena_x86_64-el9-gcc15-opt/2026-11-23T2100/AthenaExternals/25.0.81/InstallArea/x86_64-el9-gcc15-opt
export NN_STUDY_LCG=/cvmfs/atlas-nightlies.cern.ch/repo/sw/main_Athena_x86_64-el9-gcc15-opt/sw/lcg/releases/LCG_110_ATLAS_10
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NN_STUDY_MODEL_DIR=$NN_STUDY_ROOT/models
export LD_LIBRARY_PATH=$NN_STUDY_ROOT/build:$NN_STUDY_LCG/blas/0.3.33/x86_64-el9-gcc15-opt/lib:$LD_LIBRARY_PATH
