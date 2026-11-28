#!/usr/bin/env python3
"""Run isolated run.sh variants in parallel, retaining every log and exit code.

usage: batch.py OUT EVENTS SKIP VARIANT... [--parallel 3] [--threads 8] [--scoring 1]
                [--env KEY=VALUE ...] [--input RDO,...] [--max-bytes N] [--min-free N]
OUT/<variant>/ is the run.sh output, OUT/<variant>.driver.log its driver log.
--env sets run.sh environment (e.g. LIB=native NN=1); --input sets INPUT.
--min-free (bytes): refuse to start and stop a running job (killpg) when free disk falls below.
--max-bytes: stop a running job when OUT grows beyond this size. Exit code 1 if any job failed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

RUN = Path(__file__).resolve().with_name("run.sh")


def size(path):
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def launch(out, variant, events, skip, threads=8, scoring=1, env=None,
           min_free=0, max_bytes=0, watch=None, log=None, stop_free=None):
    """run.sh into out; returns its exit code. Disk limits are checked every 5 s on watch;
    a running job is stopped below stop_free (default min_free) free bytes."""
    watch = watch or out.parent
    stop_free = min_free if stop_free is None else stop_free
    log = log or out.parent / (out.name + ".driver.log")
    if min_free and shutil.disk_usage(watch).free < min_free:
        raise RuntimeError(f"Less than {min_free / 2**30:g} GiB free before {out}")
    with log.open("x") as stream:
        process = subprocess.Popen(
            ["bash", str(RUN), str(out), variant, str(events), str(skip),
             str(threads), str(scoring)],
            env=dict(os.environ, **(env or {})),
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        if not (stop_free or max_bytes):
            return process.wait()
        while process.poll() is None:
            if (stop_free and shutil.disk_usage(watch).free < stop_free) or (
                max_bytes and size(watch) > max_bytes
            ):
                os.killpg(process.pid, signal.SIGTERM)
                process.wait()
                raise RuntimeError(f"Disk limit reached; stopped {out}")
            time.sleep(5)
        return process.returncode


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("events", type=int)
    p.add_argument("skip", type=int)
    p.add_argument("variants", nargs="+")
    p.add_argument("--parallel", type=int, default=3)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--scoring", type=int, default=1)
    p.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--input", help="comma-separated RDOs (run.sh INPUT)")
    p.add_argument("--max-bytes", type=float, default=0)
    p.add_argument("--min-free", type=float, default=0)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    env = dict(e.split("=", 1) for e in a.env)
    if a.input:
        env["INPUT"] = a.input

    def run(variant):
        rc = launch(a.output / variant, variant, a.events, a.skip, a.threads,
                    a.scoring, env, int(a.min_free), int(a.max_bytes), a.output)
        print(variant, rc, flush=True)
        return rc

    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        codes = list(pool.map(run, a.variants))
    raise SystemExit(int(any(codes)))
