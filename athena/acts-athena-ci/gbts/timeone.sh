#!/bin/bash
# usage: timeone.sh <build: pr|base> <strategy: Gbts|GbtsFtf> <tag> [nevents]
BUILD=$1
STRATEGY=$2
TAG=$3
NEVENTS=${4:-20}
case $BUILD in
  pr)   BDIR=/home/astefl/source/acts/acts-athena-ci/athena-build ;;
  base) BDIR=/home/astefl/source/acts/acts-athena-ci/athena-build-base ;;
  *) echo "unknown build $BUILD"; exit 1 ;;
esac
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,main,2026-08-10T2100,gcc15"
source $BDIR/x86_64-el9-gcc15-opt/setup.sh
D=/home/astefl/source/acts/acts-athena-ci/run/$TAG
rm -rf $D && mkdir -p $D && cd $D
echo "=== $TAG : build=$BUILD strategy=$STRATEGY nevents=$NEVENTS start=$(date +%T) ==="
/home/astefl/scripts/athena/acts-athena-ci/gbts/gbts_time.sh $STRATEGY $NEVENTS
echo "=== $TAG done=$(date +%T) ==="
