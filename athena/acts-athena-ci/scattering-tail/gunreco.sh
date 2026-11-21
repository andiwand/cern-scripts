#!/bin/bash
# Reco variants on all RDOs of a generated sample: run/scattering-tail/g<name>/<variant>.  usage: gunreco.sh <name>...  env VARIANTS, JOBS (default 4)
S=~/scripts/athena/acts-athena-ci/scattering-tail; R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail
for n in "$@"; do for v in ${VARIANTS:-t0 c35 t35 g35 c5 t5 g5 w10}; do echo "$n $v"; done; done |
  xargs -P ${JOBS:-4} -L1 bash -c "case \$1 in g*) r=run4.sh;; *) r=run2.sh;; esac; INPUT_RDO=\$(ls $R/gen/\$0/*/RDO.pool.root | paste -sd,) PAR=1 bash $S/\$r g\$0 8 -1 \$1 | sed \"s/^/g\$0 /\""
echo GUNRECO_DONE
