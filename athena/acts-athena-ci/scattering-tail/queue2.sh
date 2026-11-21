#!/bin/bash
# after the first fastreco and its IDPVM: redo OOM-killed w10 files, then tighter cuts and the gate variant, 6 jobs at a time
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail; I=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input
while pgrep -f "scattering-tail/fastreco.sh|runIDPVM" >/dev/null; do sleep 30; done
for f in $(ls $I/RDO.*); do n=$(basename $f | grep -o '\._0000[0-9]*' | tail -c3)
  [ -f $R/f$n/w10/myAOD.pool.root ] || echo "w10 $f $n"; done |
  xargs -P 6 -L1 bash -c 'INPUT_RDO=$1 PAR=1 bash ~/scripts/athena/acts-athena-ci/scattering-tail/run2.sh f$2 8 -1 $0 | grep RECO'
JOBS=6 bash ~/scripts/athena/acts-athena-ci/scattering-tail/fastreco2.sh t4 t35 c4 c35 tg1
