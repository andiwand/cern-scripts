#!/usr/bin/bash
# Primary-pass strip seeding study on the full (non-fast) ACTS chain.
# usage: strip_exp.sh <tag> <grid|gbts> <on|off> [nevents]
# env: TABLE=<connector path>  PERFMON=1  EXTRA_POST=<python;>
TAG=$1; STRAT=$2; PIX=$3; NEV=${4:-5}
input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
export ATHENA_CORE_NUMBER=1

CHAIN='flags.Tracking.doITkFastTracking=False; from TrkConfig.TrkConfigFlags import TrackingComponent; flags.Tracking.recoChain=[TrackingComponent.ActsLegacyChain];'
case $STRAT in
  grid) SEED='from ActsConfig.ActsConfigFlags import SeedingStrategy; flags.Tracking.ITkActsLegacyPass.SeedingStrategy=SeedingStrategy.GridTriplet;' ;;
  gbts) SEED='from ActsConfig.ActsConfigFlags import SeedingStrategy; flags.Tracking.ITkActsLegacyPass.SeedingStrategy=SeedingStrategy.Gbts;' ;;
  *) echo "bad strategy $STRAT"; exit 1 ;;
esac
case $PIX in
  on)  PIXFLAG='' ;;
  off) PIXFLAG='flags.Acts.Seeds.disablePixelSeeding=True;' ;;
  *) echo "bad pixels $PIX"; exit 1 ;;
esac

POSTPARTS=""
[ -n "$TABLE" ] && POSTPARTS="${POSTPARTS}cfg.getEventAlgo('ActsLegacyStripSeedingAlg').SeedTool.connectorInputFile='${TABLE}';"
[ -n "$EXTRA_POST" ] && POSTPARTS="${POSTPARTS}${EXTRA_POST}"
POST=()
[ -n "$POSTPARTS" ] && POST=(--postExec "$POSTPARTS")
PM=()
[ -n "$PERFMON" ] && PM=(--perfmon 'fullmonmt')

Reco_tf.py \
  --maxEvents ${NEV} \
  --multithreaded 'False' \
  "${PM[@]}" \
  --conditionsTag "all:${conditions}" \
  --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude" \
  --steering 'doRAWtoALL' \
  --preExec "flags.Exec.FPE=-1; ${CHAIN} ${SEED} ${PIXFLAG}" \
  "${POST[@]}" \
  --inputRDOFile ${input_rdo} \
  --outputAODFile 'AOD.pool.root' > reco.log 2>&1
echo "RECO RC=$? TAG=$TAG"
