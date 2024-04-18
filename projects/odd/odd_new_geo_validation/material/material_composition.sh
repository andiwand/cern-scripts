#!/usr/bin/env bash

input=$1
output=$2

ActsAnalysisMaterialComposition \
      -i $input \
      -o $output \
      --sub-names all beampipe pixel sstrips lstrips solenoid \
      --sub-rmin 0:0:25:200:680:1100 \
      --sub-rmax 2000:25:200:680:1100:2000 \
      --sub-zmin -3200:-3200:-3200:-3200:-3200:-3200 \
      --sub-zmax 3200:3200:3200:3200:3200:3200 \
      -s
