#!/bin/bash
# after the first fastreco and its IDPVM: redo failed t5/w10 files, then tighter cuts and the gate variant, 6 jobs at a time
while pgrep -f "scattering-tail/fastreco.sh|runIDPVM" >/dev/null; do sleep 30; done
S=~/scripts/athena/acts-athena-ci/scattering-tail
bash $S/redo.sh t5 w10
JOBS=6 bash $S/fastreco2.sh t4 t35 c4 c35 tg1
bash $S/redo.sh t4 t35 c4 c35 tg1
echo QUEUE3_DONE
