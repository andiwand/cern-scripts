"""Run scheduler scaling sequentially and require exact per-event output hashes.
Keeps all CSVs from the first run; later redundant CSVs are removed after hashing.
"""

import argparse, hashlib, json, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ["source", "build", "input", "material-map", "module-dir", "output"]:
    p.add_argument("--" + name, type=Path, required=True)
p.add_argument("--revision", required=True)
p.add_argument("--events", type=int, default=20)
p.add_argument("--repeats", type=int, default=3)
p.add_argument("--threads", type=int, nargs="+", default=[1, 2, 4, 8])
p.add_argument(
    "--environment",
    type=Path,
    default=Path(__file__).resolve().parents[2]
    / "fatras-neutral-hadrons/odd/run-env.sh",
)
a = p.parse_args()
if min(a.events, a.repeats, *a.threads) < 1:
    p.error("counts must be positive")
a.output.mkdir(parents=True, exist_ok=False)
runner = Path(__file__).resolve().parent.parent / "run.py"
records = []
expected = None
for repeat in range(a.repeats):
    for n in a.threads if repeat % 2 == 0 else a.threads[::-1]:
        dest = a.output / f"r{repeat}-w{n}"
        cmd = [
            str(a.environment),
            str(runner),
            "--mode",
            "live",
            "--source",
            str(a.source),
            "--build",
            str(a.build),
            "--input",
            str(a.input),
            "--material-map",
            str(a.material_map),
            "--module-dir",
            str(a.module_dir),
            "--revision",
            a.revision,
            "--events",
            str(a.events),
            "--threads",
            str(n),
            "--output",
            str(dest),
        ]
        with dest.with_suffix(".log").open("w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
        hashes = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in dest.glob("event*.csv")
        }
        if len(hashes) != 2 * a.events:
            raise RuntimeError("missing event CSV output")
        first = expected is None
        if first:
            expected = hashes
        if hashes != expected:
            raise RuntimeError(f"event output mismatch: {dest}")
        d = json.loads((dest / "metadata.json").read_text())
        d.update(repeat=repeat, command=cmd, output_sha256=hashes)
        records.append(d)
        (a.output / "runs.json").write_text(json.dumps(records, indent=2))
        print(repeat, n, d["sequencer_seconds"], d["sequencer_cpu_seconds"], flush=True)
        if not first:
            for file in dest.glob("event*.csv"):
                file.unlink()
