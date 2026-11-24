#!/usr/bin/env python3
"""Matched serial raw/NN control after the backend comparison has finished."""
import argparse
import json
import subprocess
import time
from pathlib import Path

S = Path(__file__).resolve().parent
R = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
U = R/'uncalibrated-reference'
U.mkdir(exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--standalone',action='store_true');args=p.parse_args()
while not args.standalone and len(list((R/'integrated').glob('c*/*/complete.txt'))) != 30:
    time.sleep(5)
# Let the pending report extraction/render finish before starting timed jobs.
while not args.standalone and not (R/'report-generated.txt').exists():
    time.sleep(5)

for cycle in range(1, 4):
    order = ['raw', 'post'] if cycle != 2 else ['post', 'raw']
    for calibration in order:
        run = U/f'c{cycle}'/calibration
        if (run/'complete.txt').exists():
            continue
        backend = 'original' if calibration == 'raw' else 'direct_blocked'
        subprocess.run(['python3',str(S/'run_quiet_job.py'),str(run),backend,
                        '--calibration',calibration],check=True)
        print(cycle, calibration, 'complete', flush=True)
        subprocess.run(['python3', str(S/'summarize_uncalibrated.py')], check=True)
(U/'complete.txt').write_text('ok\n')
print('Matched uncalibrated reference complete', flush=True)
