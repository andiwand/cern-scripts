#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPTS_DIR=$SCRIPT_DIR/../..

FULL_CHAIN=$SCRIPT_DIR/full_chain_perf.py

ACTS_ACTIVATE_1=~/cern/source/acts/acts/perf1/activate.sh
ACTS_ACTIVATE_2=~/cern/source/acts/acts/perf2/activate.sh

$SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_1 python3 $FULL_CHAIN --ttbar perf_main
$SCRIPTS_DIR/generic/activate_and_run.sh $ACTS_ACTIVATE_2 python3 $FULL_CHAIN --ttbar perf_changed
