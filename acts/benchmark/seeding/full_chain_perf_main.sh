#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPTS_DIR=$SCRIPT_DIR/../../..

FULL_CHAIN=$SCRIPT_DIR/full_chain_perf_main.py

ACTS_ACTIVATE_1=~/cern/source/acts/acts/perf1/activate.sh

cd $SCRIPT_DIR
mkdir -p results_main

#exec $SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_1 spyral run -o results_main/spyral.csv -l main -- python3 -u $FULL_CHAIN --ttbar results_main | tee results_main/log.txt
exec $SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_1 exec python3 -u $FULL_CHAIN --geant4 /Users/andreas/cern/thesis/data/odd-performance/sim/ttbar-pu200_geant4 results_main
