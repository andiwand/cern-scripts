#!/usr/bin/bash
# usage: pix_common.sh <core|trk> [nevents] [extra preExec]
VARIANT=${1:-trk}
NEV=${2:-20}
EXTRA=${3:-}
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
case $VARIANT in
  core) STRAT='from ActsConfig.ActsConfigFlags import SpacePointStrategy; flags.Acts.PixelSpacePointStrategy=SpacePointStrategy.ActsCore;' ;;
  trk)  STRAT='from ActsConfig.ActsConfigFlags import SpacePointStrategy; flags.Acts.PixelSpacePointStrategy=SpacePointStrategy.ActsTrk;' ;;
  *) echo "unknown variant $VARIANT"; exit 1 ;;
esac
Reco_tf.py \
  --maxEvents $NEV \
  --perfmon 'fullmonmt' \
  --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
  --steering 'doRAWtoALL' \
  --preExec "flags.Exec.FPE=-1; flags.Acts.doLargeRadius=True; ${STRAT} ${EXTRA}" \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
