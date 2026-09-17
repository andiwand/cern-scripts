#!/bin/bash
source /home/astefl/source/acts/acts-athena-ci/runenv.sh >/dev/null 2>&1
cd /home/astefl/source/acts/acts-athena-ci/run
for v in core trk; do
  d=prof_$v
  rm -rf $d; mkdir -p $d; cd $d
  sed 's/--maxEvents 20/--maxEvents 5/' /home/astefl/scripts/athena/acts-athena-ci/strip-space-points/stgap0_$v.sh > run.sh
  nice -n 5 perf record -F 999 -o perf.data --  bash run.sh > /dev/null 2>&1
  echo "recorded $d"
  cd ..
done
echo "PROF DONE"
