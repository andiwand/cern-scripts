#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/gbts/gbtsrunenv.sh >/dev/null 2>&1
D=/home/astefl/source/acts/acts-athena-ci/run/exp_$1
rm -rf $D; mkdir -p $D && cd $D
/home/astefl/scripts/athena/acts-athena-ci/gbts/strip_exp.sh "$@"
