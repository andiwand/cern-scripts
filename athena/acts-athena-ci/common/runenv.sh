#!/bin/bash
# Run environment of a study: its env.sh plus the build's setup.sh.  usage: source runenv.sh <study>
source ~/scripts/athena/acts-athena-ci/$1/env.sh
source $ACI_BASE/$BUILD_DIR/x86_64-el9-gcc15-opt/setup.sh
