#!/bin/bash
# Single-particle full sim + no-pile-up digi (RUN4 default geometry) into run/scattering-tail/gen/<name>/<job>/RDO.pool.root
# usage: gen.sh <name> <pid> <pt GeV> <job> <nevents>
source ~/scripts/athena/acts-athena-ci/scattering-tail/env.sh >/dev/null 2>&1
export PYTHONPATH=~/scripts/athena/acts-athena-ci/scattering-tail/pyfrag:$PYTHONPATH TAILGUN_PID=$2 TAILGUN_PT=$3
O=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail/gen/$1/$4; rm -rf $O; mkdir -p $O; cd $O
geo=$(python -c "from AthenaConfiguration.TestDefaults import defaultGeometryTags as g; print(g.RUN4)")
cond=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags as d; print(d.RUN4_MC)")
Sim_tf.py --multithreaded False --simulator FullG4MT_QS ${SIMDET:+--detectors $SIMDET} --geometryVersion "default:$geo" --conditionsTag "default:$cond" \
  --preInclude "EVNTtoHITS:Campaigns.MC23PhaseIISimulation" --postInclude "default:PyJobTransforms.UseFrontier" \
  --preExec "EVNTtoHITS:flags.Sim.GenerationConfiguration=\"TailGun.TailGunCfg\"" \
  --randomSeed $((1000 + $4)) --jobNumber $(( $4 + 1 )) --maxEvents $5 --outputHITSFile HITS.pool.root --imf False > sim.log 2>&1 || { echo "$1/$4 SIM FAIL"; exit 1; }
ATHENA_CORE_NUMBER=${NT:-4} Digi_tf.py --multithreaded True --conditionsTag "default:$cond" ${SIMDET:+--detectors ITkPixel ITkStrip} --digiSeedOffset1 $((170 + $4)) --digiSeedOffset2 $((170 + $4)) \
  --inputHITSFile HITS.pool.root --jobNumber $(( $4 + 1 )) --maxEvents -1 --outputRDOFile RDO.pool.root \
  --postInclude "PyJobTransforms.UseFrontier" --preInclude "HITtoRDO:Campaigns.MC23PhaseIINoPileUp" > digi.log 2>&1 || { echo "$1/$4 DIGI FAIL"; exit 1; }
echo "$1/$4 OK"
