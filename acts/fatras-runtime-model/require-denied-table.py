#!/usr/bin/env python3
"""Fail unless TABLE is unreadable, then run RUNNER with its remaining arguments."""

import json, runpy, sys
from pathlib import Path

blocked = Path(sys.argv[1])
proof = Path(sys.argv[2])
runner = sys.argv[3:]
try:
    with blocked.open("rb") as f:
        f.read(1)
except PermissionError:
    proof.write_text(
        json.dumps(
            {
                "path": str(blocked),
                "open_result": "PermissionError",
                "simulation_argv": runner,
            },
            indent=2,
        )
        + "\n"
    )
else:
    raise RuntimeError("Custom library is still readable: proof failed")
sys.argv = runner
runpy.run_path(sys.argv[0], run_name="__main__")
