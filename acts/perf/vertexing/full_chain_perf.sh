#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPTS_DIR=$SCRIPT_DIR/../../..

FULL_CHAIN=$SCRIPT_DIR/full_chain_perf.py

ACTS_ACTIVATE_1=~/cern/source/acts/acts/dev3/activate.sh

mkdir -p results

$SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_1 python3 -u $FULL_CHAIN results --ttbar | tee results/log.txt
