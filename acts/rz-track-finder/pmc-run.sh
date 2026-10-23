#!/bin/bash
# usage: pmc-run.sh <tag> <batch>  -- ITk ttbar PU200 5 ev under the CPU Counters template, tables exported
SP=/private/tmp/claude-501/-Users-andreas-cern-source-acts-acts-dev3/ee4a685f-75e5-41f0-a119-bc732fa04ecc/scratchpad
source $SP/env-rel.sh >/dev/null 2>&1
cd ~/cern/scripts/acts/rz-track-finder
TAG=$1; BATCH=$2
rm -rf $SP/$TAG.trace
xctrace record --template 'CPU Counters' --instrument 'Points of Interest' --output $SP/$TAG.trace --launch -- $(which python) compare.py --finder rz --itk --ttbar --pileup 200 --max-holes 8 --max-consecutive-holes 4 --material-tables --batch $BATCH --out $SP/$TAG --events 5 --log INFO > $SP/$TAG.log 2>&1
grep -h "RzTrackFinding timing" $SP/$TAG.log | sed 's/.*find /find /' | cut -c1-60
xctrace export --input $SP/$TAG.trace --xpath '/trace-toc/run[@number="1"]/data/table[@schema="os-signpost"]' > $SP/$TAG-signpost.xml 2>/dev/null
xctrace export --input $SP/$TAG.trace --xpath '/trace-toc/run[@number="1"]/data/table[@schema="kdebug-counters-with-time-sample"]' > $SP/$TAG-counters.xml 2>/dev/null
ls -la $SP/$TAG-signpost.xml $SP/$TAG-counters.xml
