#!/bin/bash
# usage: rz2_phys.sh <tag> [parallel]
# Physics: {old,newgrid,new} x {ckf,rz} x {ttbar 100, pt10 200, pt100 200}, reco + IDPVM,
# into run/<tag>_<sample>_<side>_<v>. Parallel: never while timing.
R=/home/astefl/source/acts/acts-athena-ci/run
TAG=${1:-ph}
P=${2:-8}
for sample in ttbar pt10 pt100; do
  for side in old newgrid new; do
    for v in ckf rz; do
      n=200; [ $sample = ttbar ] && n=100
      echo "$side $v $sample $n $R/${TAG}_${sample}_${side}_${v}"
    done
  done
done | xargs -P $P -L 1 bash -c 'bash '$R'/rz2_job.sh "$0" "$1" "$2" "$3" "$4" 1 > "$4.out" 2>&1; echo "$4 $(paste -sd" " "$4.out")"'
echo "RZ2PHYS_${TAG}_DONE"
