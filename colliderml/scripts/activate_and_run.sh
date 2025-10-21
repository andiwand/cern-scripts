#!/usr/bin/env bash

# get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# activate environment
source $SCRIPT_DIR/activate.sh

# run command
$@
