#!/usr/bin/env python3
"""Wait for sustained lower host load; never interfere with other users' jobs."""
import os
import time

quiet_since = None
last_report = 0
while True:
    now = time.monotonic()
    load = os.getloadavg()
    if load[0] < 12 and load[1] < 15:
        quiet_since = now if quiet_since is None else quiet_since
        if now-quiet_since >= 60:
            print('Lower-load window confirmed:', load, flush=True)
            break
    else:
        quiet_since = None
    if now-last_report >= 60:
        print('Waiting for lower host load:', load, flush=True)
        last_report = now
    time.sleep(10)
