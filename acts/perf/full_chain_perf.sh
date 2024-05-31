#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

$SCRIPTS_DIR/full_chain_perf_main.sh
$SCRIPTS_DIR/full_chain_perf_changed.sh
