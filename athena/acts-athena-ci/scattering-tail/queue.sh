#!/bin/bash
# after the first fastreco: tighter cuts and the gate variant
while pgrep -f "scattering-tail/fastreco.sh" >/dev/null; do sleep 30; done
bash ~/scripts/athena/acts-athena-ci/scattering-tail/fastreco2.sh t4 t35 c4 c35 tg1
