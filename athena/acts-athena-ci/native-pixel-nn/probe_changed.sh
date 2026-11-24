#!/bin/bash
cd /home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > env.log 2>&1
set -e
for n in number pos1 pos2 pos3; do ./probe $n.changed.onnx $n.changed.graph; done
sha256sum *.changed.graph
