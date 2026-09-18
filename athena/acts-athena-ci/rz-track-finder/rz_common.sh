#!/usr/bin/bash
# usage: rz_common.sh <ckf|rz> [nevents] [extra preExec]
# Reconstruction with the CKF or the RZ track finder, same seeds either way.
VARIANT=${1:-ckf}
NEV=${2:-20}
EXTRA=${3:-}
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
case $VARIANT in
  ckf) STRAT='from ActsConfig.ActsConfigFlags import TrackFindingStrategy; flags.Acts.TrackFindingStrategy=TrackFindingStrategy.Ckf;' ;;
  rz)  STRAT='from ActsConfig.ActsConfigFlags import TrackFindingStrategy; flags.Acts.TrackFindingStrategy=TrackFindingStrategy.Rz;' ;;
  *) echo "unknown variant $VARIANT"; exit 1 ;;
esac
Reco_tf.py \
  --maxEvents $NEV \
  --perfmon 'fullmonmt' \
  --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
  --steering 'doRAWtoALL' \
  --preExec "flags.Exec.FPE=-1; ${STRAT} ${EXTRA}" \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
