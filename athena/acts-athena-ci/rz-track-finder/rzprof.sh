#!/bin/bash
# perf profile of the RZ reconstruction with DWARF call stacks, for the makeTrack breakdown
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzrunenv.sh >/dev/null 2>&1
R=/home/astefl/source/acts/acts-athena-ci/run
NEV=${1:-10}
cd $R
d=profhi_rz; rm -rf $d; mkdir -p $d; cd $d
cat > go.sh <<INNER
bash /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz_common.sh rz $NEV
INNER
echo "start $(date +%T) load=$(cut -d" " -f1 /proc/loadavg)"
nice -n 5 perf record -e cycles:u -F 3999 --call-graph dwarf,4096 -m 32 -o perf.data -- bash go.sh > perf.out 2>&1
echo "PROFHI_RC=$? $(ls -la perf.data 2>/dev/null | awk "{print \$5}") end $(date +%T)"
grep -h "RZ seed loop" log.RAWtoALL | sed "s/.*INFO //"
echo PROFHI_DONE
