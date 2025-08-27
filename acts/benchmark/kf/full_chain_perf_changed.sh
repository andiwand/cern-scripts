#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPTS_DIR=$SCRIPT_DIR/../../..

FULL_CHAIN=$SCRIPT_DIR/full_chain_perf.py

ACTS_ACTIVATE_2=~/cern/source/acts/acts/perf2/activate.sh

cd $SCRIPT_DIR
mkdir -p results_changed

#exec $SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_2 spyral run -o results_changed/spyral.csv -l changed -- python3 -u $FULL_CHAIN --ttbar results_changed | tee results_changed/log.txt
exec $SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_2 exec python3 -u $FULL_CHAIN --geant4 /Users/andreas/cern/thesis/data/odd-performance/sim/ttbar-pu200_geant4 results_changed
