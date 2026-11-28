"""Existing 10 GeV muon RDOs; tight/loose gates and NN/tail factorial controls."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import shutil
import signal
import time

A = Path("/home/astefl/source/acts/acts-athena-ci")
S = Path(__file__).parent
R = A / "run/scattering-tail-score/gun"
R.mkdir()
jobs = [
    (cal, var, group)
    for cal in ["raw", "nn"]
    for var in ["core4", "core7", "tail4"]
    for group in range(5)
]
(R / "plan.json").write_text(
    json.dumps(
        dict(
            sample="mu10",
            events_per_group=1000,
            groups=5,
            calibration="pre, all charges/sizes, primary only",
            jobs=jobs,
        ),
        indent=2,
    )
    + "\n"
)


def run(job):
    cal, var, group = job
    out = R / f"{cal}-{var}" / str(group)
    out.parent.mkdir(exist_ok=True)
    env = dict(
        os.environ,
        NN_MODE="pre",
        GUN_CALIBRATION=cal,
        GUN_INPUT=str(A / f"run/error-budget/gen/mu10/{group}/RDO.pool.root"),
    )
    with out.with_suffix(".driver.log").open("x") as log:
        assert shutil.disk_usage(R).free > 22 * 2**30, "Keep 22 GiB free"
        process = subprocess.Popen(
            ["bash", str(S / "run_gun.sh"), str(out), var, "1000", "0", "2"],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        while process.poll() is None:
            used = sum(p.stat().st_size for p in R.rglob("*") if p.is_file())
            if used > 2 * 2**30 or shutil.disk_usage(R).free < 22 * 2**30:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait()
                raise RuntimeError(
                    "Gun disk budget exceeded: 2 GiB maximum, 22 GiB free reserve"
                )
            time.sleep(5)
        rc = process.returncode

    print(job, rc, flush=True)
    return rc


with ThreadPoolExecutor(max_workers=3) as pool:
    codes = list(pool.map(run, jobs))
(R / "exit-code").write_text(str(int(any(codes))) + "\n")
raise SystemExit(int(any(codes)))
