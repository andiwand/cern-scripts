#!/usr/bin/bash
# SPOT-style check: usage rzspot.sh <ckf|rz> <nthreads> <nevents>
VARIANT=${1:-rz}
NTHREADS=${2:-1}
NEVENTS=${3:-5}
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
case $VARIANT in
  ckf) STRAT='TrackFindingStrategy.Ckf' ;;
  rz)  STRAT='TrackFindingStrategy.Rz' ;;
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
    --preExec "from ActsConfig.ActsConfigFlags import TrackFindingStrategy; flags.Acts.TrackFindingStrategy=${STRAT};" \
    --postExec 'all:cfg.getService("AlgResourcePool").CountAlgorithmInstanceMisses = True;' \
    --inputRDOFile ${input_rdo} \
    --outputAODFile 'myAOD.pool.root' \
    --jobNumber '1' > reco.log 2>&1
echo "SPOT RC=$?"
