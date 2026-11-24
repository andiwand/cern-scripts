#!/usr/bin/env python3
"""Replace two overloaded backend runs, then obtain the matched raw control."""
import subprocess
from pathlib import Path

S = Path(__file__).resolve().parent
R = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
subprocess.run(['python3',str(S/'uncalibrated_reference.py'),'--standalone'],check=True)
for backend in ['ort_simple','direct']:
    subprocess.run(['python3',str(S/'run_quiet_job.py'),str(R/'integrated/c3'/backend),backend],check=True)
subprocess.run(['bash',str(S/'finalize_report.sh')],check=True)
print('Lower-load recovery and raw reference complete',flush=True)
