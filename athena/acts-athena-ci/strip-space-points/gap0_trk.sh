#!/usr/bin/bash
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions_tag=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
Reco_tf.py \
  --preExec "flags.Exec.FPE=-1; flags.Detector.EnableCalo=True; flags.Detector.EnableHGTD=True; flags.Acts.doLargeRadius=True; flags.Acts.doLowPt=True;" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
  --postExec "cfg.getEventAlgo('ActsStripSpacePointFormationAlg').SpacePointFormationTool.StripGapParameter=0.0" \
  --conditionsTag ${conditions_tag} \
  --inputRDOFile ${input_rdo} \
  --outputAODFile AOD.pool.root \
  --maxEvents 5 \
  --multithreaded > reco.log 2>&1
echo "RECO RC=$?"
