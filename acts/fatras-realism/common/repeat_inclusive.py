#!/usr/bin/env python3
"""Serial, alternating inclusive_run.py repetitions for CPU timing and replay checks.

  repeat_inclusive.py --work WORK \
      --variant "control=OLD/pruned-build" --variant "current=WORK/pruned-build" \
      --single "disabled=WORK/pruned-build --disable-annihilation" \
      --standard WORK/bridge --standard-threads 1 4  [inclusive_run options]

Each --variant "NAME=MODULE [inclusive_run args]" runs --repeats times as
WORK/NAME-i with --mode live --soft (bounded soft transport); the order
alternates between repeats. --single variants run once as WORK/NAME. With
--standard, the bridge runs with standard navigation as WORK/standard-N for
each worker count N (event CSVs must then agree across N). Unknown options are
passed to every run. Do not run other CPU-intensive jobs concurrently.
"""

import argparse, json, shlex, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def spec(text):
    name, rest = text.split("=", 1)
    module, *extra = shlex.split(rest)
    return name, module, extra


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--variant", type=spec, action="append", default=[])
p.add_argument("--single", type=spec, action="append", default=[])
p.add_argument("--repeats", type=int, default=3)
p.add_argument("--standard", type=Path, help="Bridge for standard-navigation worker checks")
p.add_argument("--standard-threads", type=int, nargs="+", default=[1, 4])
a, common = p.parse_known_args()


def run(name, args):
    out = a.work / name
    cmd = [sys.executable, str(HERE / "inclusive_run.py"), "--mode", "live", "--output", str(out), *args, *common]
    subprocess.run(cmd, check=True)
    meta = json.loads((out / "metadata.json").read_text())
    return {"name": name, "cpu_s_per_event": meta["sequencer_cpu_seconds"] / meta["events"], "output": str(out)}


records = []
for i in range(a.repeats):
    order = a.variant if i % 2 == 0 else a.variant[::-1]
    for name, module, extra in order:
        records.append(dict(run(f"{name}-{i}", ["--soft", "--module-dir", module, *extra]), variant=name, repeat=i))
        (a.work / "repeated-timings.json").write_text(json.dumps(records, indent=2))
for name, module, extra in a.single:
    records.append(run(name, ["--soft", "--module-dir", module, *extra]))
if a.standard:
    for threads in a.standard_threads:
        records.append(run(f"standard-{threads}", ["--module-dir", str(a.standard), "--threads", str(threads)]))
(a.work / "repeated-timings.json").write_text(json.dumps(records, indent=2))
