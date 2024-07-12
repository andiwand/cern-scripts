#!/usr/bin/env bash

# default or first argument
WORKDIR=${1:-$HOME/cern/source/acts/acts-athena-ci}

tmux attach-session -t "acts-athena-ci" && exit 0

tmux new-session -s "acts-athena-ci" \; \
  send-keys "cd $WORKDIR; clear" C-m \; \
  split-window -h \; \
  send-keys "cd $WORKDIR/acts; clear" C-m \; \
  split-window -v \; \
  send-keys "cd $WORKDIR/athena; clear" C-m \;
