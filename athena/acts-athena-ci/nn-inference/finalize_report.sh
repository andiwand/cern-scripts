#!/usr/bin/env bash
# Run only after all reconstruction and standalone comparisons have completed.
set -eo pipefail
nn_scripts=/home/astefl/scripts/athena/acts-athena-ci/nn-inference
nn_results=/home/astefl/source/acts/acts-athena-ci/run/nn-inference
python3 "$nn_scripts/summarize.py" > "$nn_results/final-summary.log"
python3 "$nn_scripts/audit.py"
python3 "$nn_scripts/compare_outcomes.py" > "$nn_results/outcome-comparison.log"
python3 "$nn_scripts/calibration_fraction.py" > "$nn_results/calibration-fraction.log"
python3 "$nn_scripts/count_loc.py" > "$nn_results/loc-counts.log"
set +e
source "$nn_scripts/env.sh" > "$nn_results/report-environment.log" 2>&1
set -e
python3 "$nn_scripts/kernel_summary.py" > "$nn_results/kernel-summary.log"
python3 "$nn_scripts/plot.py"
python3 "$nn_scripts/kernel_plot.py"
source "$nn_scripts/athena_preload.sh"
python3 "$nn_scripts/provenance.py"
python3 "$nn_scripts/update_note.py"
env -u PYTHONHOME -u PYTHONPATH -u LD_PRELOAD /tmp/nn-model-inspection/bin/python "$nn_scripts/render_note.py"
date -u +%FT%TZ > "$nn_results/report-generated.txt"
