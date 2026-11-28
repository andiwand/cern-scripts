"""Summarize the 18 serial compiler observations produced by compile_benchmark.py."""

import json
import os
import statistics
from pathlib import Path

base = Path(os.environ.get("ACTS_EDM_EXPERIMENT_ROOT", "/private/tmp/acts-edm-2026-10-31"))
results = base / "results"
records = json.loads((results / "compile/results.json").read_text())
assert len(records) == 18
summary = {}
for source in sorted({record["source"] for record in records}):
    summary[source] = {}
    for variant in ["main", "vector", "any"]:
        samples = [r for r in records if r["source"] == source and r["variant"] == variant]
        assert sorted(r["block"] for r in samples) == [0, 1, 2]
        metrics = {
            key: statistics.median(r[key] for r in samples)
            for key in ["wall_s", "user_s", "system_s", "rss_bytes", "object_bytes"]
        }
        metrics["cpu_s"] = statistics.median(r["user_s"] + r["system_s"] for r in samples)
        metrics["wall_range_s"] = [min(r["wall_s"] for r in samples), max(r["wall_s"] for r in samples)]
        summary[source][variant] = metrics
(results / "compile-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
