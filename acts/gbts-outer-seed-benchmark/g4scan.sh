#!/bin/zsh
source /Users/andreas/cern/source/acts/acts/dev3/activate.sh >/dev/null 2>&1
source ~/cern/data/geant4/11.3/env.sh
cd /private/tmp/claude-501/-Users-andreas-cern-source-acts-acts-dev3/454db880-38eb-4c1d-963a-d16b7952c81c/scratchpad
for k in 0 1 2 3 4; do
  python memrun.py g4sim.py --output g4_part$k --events 8 --skip $((k*8)) > g4_part$k.log 2> g4_part$k.err &
done
wait
grep -h MEMRUN g4_part*.err
grep -l "Assert\|Traceback" g4_part*.err && echo "some part failed"
echo "g4 sim done $(date +%T)"
