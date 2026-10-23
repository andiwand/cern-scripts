#!/usr/bin/env python3
"""Sequential measurements; no concurrent simulation/analysis timing jobs."""

import argparse, subprocess, os, json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument(
    "--input", type=Path, default=Path("/private/tmp/fatras-odd-inputs-final")
)
p.add_argument("--variant", required=True)
p.add_argument("--events", type=int, default=1)
p.add_argument("--revision", required=True)
p.add_argument("--output", type=Path, required=True)
a, extra = p.parse_known_args()
base = Path(__file__).parent
build = "/Users/andreas/cern/build/acts/acts/dev3"
cmd = [
    "bash",
    "/Users/andreas/cern/scripts/acts/fatras-realism/fatras-neutral-hadrons/odd/run-env.sh",
    str(base / "run.py"),
    "--module-dir",
    str(base / "build"),
    "--runner",
    "/Users/andreas/cern/scripts/acts/fatras-realism/fatras-charged-mesons/run-comparison.py",
    *extra,
    "--mode",
    "changed",
    "--source",
    "/Users/andreas/cern/source/acts/acts/dev3",
    "--build",
    build,
    "--revision",
    a.revision,
    "--input",
    str(a.input),
    "--output",
    str(a.output),
    "--material-map",
    "/Users/andreas/cern/scripts/acts/fatras-realism/fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root",
    "--table",
    "/Users/andreas/cern/scripts/acts/fatras-realism/fatras-neutral-refinement/data/2026-10-14/silicon-all-low.table",
    "--events",
    str(a.events),
]
env = dict(os.environ)
env["ACTS_VALIDATION_BUILD"] = build
with Path(str(a.output) + ".log").open("w") as log:
    result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
Path(str(a.output) + "-command.json").write_text(
    json.dumps(
        {"variant": a.variant, "command": cmd, "returncode": result.returncode},
        indent=2,
    )
    + "\n"
)
result.check_returncode()
