#!/usr/bin/env python3
"""Record source revisions, input metadata and binary/script hashes.

usage: provenance.py [RUN]   (default run/scattering-tail-score) -> RUN/provenance.json, includes RUN/frozen-plan.json
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from PyUtils.MetaReader import read_metadata

base = Path("/home/astefl/source/acts/acts-athena-ci")
run = Path(sys.argv[1]) if len(sys.argv) > 1 else base / "run/scattering-tail-score"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(tree, *args):
    return subprocess.check_output(
        ["git", "-C", str(base / tree), *args], text=True
    ).strip()


result = {
    "sources": {
        t: {
            "commit": git(t, "rev-parse", "HEAD"),
            "status": git(t, "status", "--short"),
        }
        for t in ["athena-tail-score", "acts-tail-score"]
    },
    "nightly": "2026-11-19T2100",
    "platform": "x86_64-el9-gcc15-opt",
    "input_files": [
        str(p) for p in sorted((base / "run/edge-holes/input").glob("RDO.*"))
    ],
}
metadata = read_metadata(result["input_files"][0], mode="full")
result["first_input_metadata"] = {}


def walk(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            key = path + "/" + str(k)
            if any(
                s.lower() in str(k).lower()
                for s in [
                    "simflavour",
                    "simulator",
                    "physicslist",
                    "g4version",
                    "geometryversion",
                    "geoatlas",
                    "conditions",
                    "mc_channel",
                    "run_number",
                    "file_guid",
                    "nentries",
                    "pileup",
                    "interactionspercrossing",
                ]
            ):
                if isinstance(v, (str, int, float, bool, list)):
                    result["first_input_metadata"][key] = v
            walk(v, key)


walk(metadata)
lib = base / "athena-build-tail-score/x86_64-el9-gcc15-opt/lib"
result["binary_sha256"] = {
    n: sha(lib / n)
    for n in ["libActsCore.so", "libActsTrackReconstruction.so", "libActsEventCnv.so"]
}
scripts = Path(__file__).parent
result["script_sha256"] = {
    p.name: sha(p) for p in sorted(scripts.iterdir()) if p.is_file()
}
result["frozen_plan"] = json.loads((run / "frozen-plan.json").read_text())
(run / "provenance.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
print(json.dumps(result["first_input_metadata"], indent=2, default=str))
