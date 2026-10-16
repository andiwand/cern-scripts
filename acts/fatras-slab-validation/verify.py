"""Replay representative saved settings with the final formatted executable."""

import argparse, hashlib, json, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument("--binary", type=Path, required=True)
a = p.parse_args()
w = a.work
selected = [
    ("refined", "primary-common-G4_Si-22-1-30-fatras-100"),
    ("refined", "primary-common-G4_Si-22-1-30-g4-1"),
    ("refined", "cascade-full-G4_Si-11-20-30-fatras-100"),
    ("refined", "cascade-full-G4_Si-11-20-30-g4-1"),
    ("attribution", "cascade-annihilation-G4_Si-22-20-30-g4-1"),
    ("attribution", "cascade-photoelectric-G4_Si-22-20-30-g4-1"),
]
(w / "replay").mkdir(exist_ok=True)
checks = {}
for folder, name in selected:
    meta = w / folder / (name + ".json")
    d = json.loads(meta.read_text())
    cmd = d["command"]
    out = w / "replay" / (name + ".csv")
    cmd[0] = str(a.binary)
    cmd[-1] = str(out)
    with out.with_suffix(".log").open("w") as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    checks[name] = out.read_bytes() == meta.with_suffix(".csv").read_bytes()
    assert checks[name], name
(w / "replay-checks.json").write_text(
    json.dumps(
        {
            "binary_sha256": hashlib.sha256(a.binary.read_bytes()).hexdigest(),
            "checks": checks,
        },
        indent=2,
    )
)
print(checks)
