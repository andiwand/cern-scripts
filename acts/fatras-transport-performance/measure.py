"""Sequential repeat timings; no concurrent builds or simulation jobs."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--repeats", type=int, default=3)
a = p.parse_args()
records = []
for repeat in range(a.repeats):
    # Alternate order to reduce a systematic warm-up / thermal bias.
    variants = ["baseline", "pruned"] if repeat % 2 == 0 else ["pruned", "baseline"]
    for variant in variants:
        out = a.work / f"timing-{variant}-{repeat}"
        subprocess.run([sys.executable, str(Path(__file__).with_name("run.py")),
            "--source", str(a.source), "--module", str(a.work / (variant + "-build")),
            "--output", str(out)], check=True)
        meta = json.loads((out / "metadata.json").read_text())
        records.append({"variant": variant, "repeat": repeat,
            "cpu_s_per_event": meta["sequencer_cpu_seconds"] / meta["events"],
            "output": str(out)})
        (a.work / "repeated-timings.json").write_text(json.dumps(records, indent=2))
