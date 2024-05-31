#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPTS_DIR=$SCRIPT_DIR/../..

FULL_CHAIN=$SCRIPT_DIR/full_chain_perf.py

ACTS_ACTIVATE_1=~/cern/source/acts/acts/perf1/activate.sh

mkdir -p results_main

$SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_1 python3 -u $FULL_CHAIN --ttbar results_main | tee results_main/log.txt
