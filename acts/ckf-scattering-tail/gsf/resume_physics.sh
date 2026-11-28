#!/bin/zsh
# GSF study, full inward flow: outward pass with the configured branching (2),
# inward pass one measurement per surface (in code), start covariance x100.
# Baselines (base15, base25, tail15, truth) are reused from the earlier runs.
D=${0:a:h}
OUT=${1:?output dir}; BASE=${2:?dir with truth, base15, base25, tail15}
. $D/env.sh >/dev/null 2>&1
. ~/cern/build/acts/acts/ckf-tail-main/this_acts_withdeps.sh
export PYTHONPATH=~/cern/source/acts/acts/ckf-tail-main/Examples/Scripts/Python:$PYTHONPATH
export ACTS_SOURCE=~/cern/source/acts/acts/ckf-tail-main
mkdir -p $OUT; cd $D
for d in truth base15 base25 tail15; do [[ -e $OUT/$d ]] || ln -s $BASE/$d $OUT/$d; done
run() { local name=$1; shift; [[ -f $OUT/$name/tracksummary_ambi.root ]] && return; python run_main.py -o $OUT/$name -n 200 -j 6 "$@" > $OUT/$name.log 2>&1; echo "$(date +%T) $name $?"; }
run fi_base15 --full-inward
run fi_tail15 --full-inward --tail
run fi_gsf2 --full-inward --mixture 2
run fi_gsf4 --full-inward --mixture 4
run fi_gsf8 --full-inward --mixture 8
