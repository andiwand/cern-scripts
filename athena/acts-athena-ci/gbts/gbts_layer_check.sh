#!/usr/bin/bash
# usage: gbts_layer_check.sh <base|pin> [nevents]
# base = the nightly alone, pin = the local Acts packages built against it.
SIDE=${1:-base}
NEV=${2:-2}
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,main,2026-09-02T2100,gcc15"
if [ "$SIDE" = pin ]; then
  source /home/astefl/source/acts/acts-athena-ci/athena-build-pin/x86_64-el9-gcc15-opt/setup.sh
fi
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
Reco_tf.py \
  --maxEvents ${NEV} \
  --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
  --steering 'doRAWtoALL' \
  --preExec "flags.Exec.FPE=-1; \
       from ActsConfig.ActsConfigFlags import SeedingStrategy; \
       flags.Tracking.ITkActsPass.SeedingStrategy=SeedingStrategy.Gbts;" \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'AOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
