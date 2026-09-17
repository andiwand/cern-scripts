#!/usr/bin/bash
# usage: gbts_time.sh <Gbts|GbtsFtf> [nevents]
STRATEGY=${1:-Gbts}
NEVENTS=${2:-20}
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1
Reco_tf.py \
  --maxEvents ${NEVENTS} \
  --perfmon 'fullmonmt' \
  --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
  --steering 'doRAWtoALL' \
  --preExec "flags.Exec.FPE=-1; \
       from ActsConfig.ActsConfigFlags import SeedingStrategy; \
       flags.Acts.SeedingStrategy=SeedingStrategy.${STRATEGY}; \
       flags.Tracking.doPixelDigitalClustering=True; \
       from ActsConfig.ActsConfigFlags import PixelCalibrationStrategy; \
       flags.Acts.PixelCalibrationStrategy=PixelCalibrationStrategy.Uncalibrated;" \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
