#!/bin/bash
# PR 5773 vs its ACTS baseline vs legacy GBTS FTF.
# Two separate builds (athena-build = PR, athena-build-base = baseline), so
# nothing is rebuilt between runs. FTF does not use ACTS GBTS, it runs in the PR build.
R=/home/astefl/source/acts/acts-athena-ci/run
N=${NEVENTS:-20}
for i in 1 2 3; do
  /home/astefl/scripts/athena/acts-athena-ci/gbts/timeone.sh base Gbts    p5773_base_$i $N
  /home/astefl/scripts/athena/acts-athena-ci/gbts/timeone.sh pr   Gbts    p5773_pr_$i   $N
  /home/astefl/scripts/athena/acts-athena-ci/gbts/timeone.sh pr   GbtsFtf p5773_ftf_$i  $N
done
echo "TIME5773_DONE"
