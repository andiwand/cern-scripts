#!/usr/bin/bash
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
Reco_tf.py \
  --maxEvents 20 \
  --perfmon 'fullmonmt' \
  --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
  --steering 'doRAWtoALL' \
  --postExec "cfg.getEventAlgo('ActsStripSpacePointFormationAlg').SpacePointFormationTool.StripGapParameter=0.0" \
  --preExec 'flags.Exec.FPE=-1; flags.Acts.doLargeRadius=True;' \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
