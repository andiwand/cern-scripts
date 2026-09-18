#!/bin/bash
# Strip timestamps and keep the algorithm statistics tables: a fingerprint of the physics output.
sed -E 's/^[0-9]{2}:[0-9]{2}:[0-9]{2} //' "$1" \
  | grep -E "^\| |Number of truth particles with hits|Space Point Formation statistics|RDO truth stat"
