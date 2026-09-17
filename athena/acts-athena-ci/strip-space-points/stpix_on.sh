#!/usr/bin/bash
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
Reco_tf.py \
  --maxEvents 20 \
  --perfmon 'fullmonmt' \
  --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsCoreValidateSpacePointsFlags" \
  --postExec "cfg.getEventAlgo('ActsPixelSpacePointFormationAlg').SpacePointFormationTool.UseSurfaceCache=True" \
  --steering 'doRAWtoALL' \
  --preExec 'flags.Exec.FPE=-1; flags.Acts.doLargeRadius=True; from ActsConfig.ActsConfigFlags import SpacePointStrategy; flags.Acts.PixelSpacePointStrategy=SpacePointStrategy.ActsCore;' \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
