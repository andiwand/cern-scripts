#!/bin/bash
# after queue4: rebuild with the ACTS_TAIL_DIAG switch, diagnostic variants d1/d2, IDPVM (two at a time), then serial CPU cycles.
S=~/scripts/athena/acts-athena-ci/scattering-tail
while ps -eo args | grep -q "^bash queue4.sh"; do sleep 30; done
bash $S/build.sh
JOBS=6 bash $S/redo3.sh d1 d2
JOBS=6 bash $S/redo3.sh d1 d2
for v in t4 t35 c4 c35 tg1 d1 d2; do SETS="hs all" bash $S/idpvm.sh $v; done
echo IDPVM_DONE
cd $S && MAX_LOAD=4 bash cycle.sh cpu 3 20 t0 t1 t5 w10 c5
echo QUEUE5_DONE
