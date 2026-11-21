#!/bin/bash
# after the running redo of t5/w10: the tighter cuts and the gate variant, only files without a successful log, 6 jobs at a time.
# Jobs take 8.5-10 GB each; do not run more than 6 next to IDPVM.
S=~/scripts/athena/acts-athena-ci/scattering-tail
while ps -eo args | grep -q "^bash .*scattering-tail/redo.sh"; do sleep 30; done
bash $S/redo.sh t5 w10
bash $S/redo.sh t4 t35 c4 c35 tg1
bash $S/redo.sh t4 t35 c4 c35 tg1
echo QUEUE4_DONE
