#!/usr/bin/bash
# Quick SPOT-style check: usage pixspot.sh <core|trk> <nthreads> <nevents>
VARIANT=${1:-core}
NTHREADS=${2:-1}
NEVENTS=${3:-5}
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
case $VARIANT in
  core) STRAT='SpacePointStrategy.ActsCore' ;;
  trk)  STRAT='SpacePointStrategy.ActsTrk' ;;
  *) echo "unknown variant $VARIANT"; exit 1 ;;
esac
export TRF_ECHO=1
ATHENA_CORE_NUMBER=${NTHREADS} Reco_tf.py \
    --maxEvents  ${NEVENTS} \
    --perfmon 'fullmonmt' \
    --multithreaded 'True' \
    --conditionsTag "all:${conditions}" \
    --postInclude 'all:PyJobTransforms.UseFrontier' \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
    --preExec "from ActsConfig.ActsConfigFlags import SpacePointStrategy; flags.Acts.PixelSpacePointStrategy=${STRAT};" \
    --postExec 'all:cfg.getService("AlgResourcePool").CountAlgorithmInstanceMisses = True;' \
    --inputRDOFile ${input_rdo} \
    --outputAODFile 'myAOD.pool.root' \
    --jobNumber '1' > reco.log 2>&1
echo "SPOT RC=$?"
