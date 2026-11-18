#!/bin/zsh
# sample the CKF of one configuration: profile.sh OUT name mode chi2m chi2o opt [warmup] [seconds]
source ${0:a:h}/../activate-perf.sh >/dev/null 2>&1 || true
OUT=${1:?}; NAME=$2; MODE=$3; C1=$4; C2=$5; OPT=$6; WARM=${7:-60}; SEC=${8:-180}
mkdir -p $OUT
cd ${0:a:h}/..
python run.py -o $OUT/$NAME -n 200 -j 1 --mode $MODE --chi2 $C1 $C2 --opt $OPT --rgate 0.05 --no-writers > $OUT/$NAME.log 2>&1 &
PID=$!
sleep $WARM
sample $PID $SEC 1 -mayDie -f $OUT/$NAME.sample.txt > /dev/null 2>&1
kill $PID
wait $PID 2>/dev/null
echo "sampled $NAME"
