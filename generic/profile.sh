#!/usr/bin/env bash

sample $1 -f output.prof
filtercalltree output.prof > output.ctree
stackcollapse-sample.awk output.ctree > output.folded
flamegraph.pl output.folded > output.svg
