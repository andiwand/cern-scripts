#!/usr/bin/bash
# GBTS seeding with the strip path wired in (LRT strip pass + pixel pass).
# usage: gbts_strip.sh [nevents]
NEV=${1:-3}
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
Reco_tf.py \
  --maxEvents ${NEV} \
  --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude" \
  --steering 'doRAWtoALL' \
  --preExec "flags.Exec.FPE=-1; \
       flags.Acts.doLargeRadius=True; \
       from ActsConfig.ActsConfigFlags import SeedingStrategy; \
       flags.Tracking.ITkActsPass.SeedingStrategy=SeedingStrategy.Gbts; \
       flags.Tracking.ITkActsLargeRadiusPass.SeedingStrategy=SeedingStrategy.Gbts;" \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'AOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
