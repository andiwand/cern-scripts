"""Reuse local generated code; all three variants use the same bytes."""
import json
import os
import shutil
from pathlib import Path

base = Path(os.environ.get("ACTS_EDM_EXPERIMENT_ROOT", "/private/tmp/acts-edm-2026-10-31"))
existing = Path.home() / "cern/build/acts/acts/dev2"
manifest = json.loads((base / "main/codegen/manifest.json").read_text())
for key, unit in manifest["units"].items():
    matches = list(existing.glob("**/codegen/*/" + unit["output"]))
    if not matches:
        continue
    target = base / "prebuilt" / key
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(matches[0], target)
