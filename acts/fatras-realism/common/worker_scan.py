#!/usr/bin/env python3
"""ACTS worker-count scaling of inclusive_run.py with exact output checks.

  worker_scan.py run --output DIR [--threads 1 2 4 8] [inclusive_run options]
  worker_scan.py plot DIR/runs.json --output PLOTS

`run` executes inclusive_run.py --mode live sequentially for each worker count,
reversing the order on alternate repeats, and requires identical per-event CSV
hashes in every run. CSVs of the first run are kept, later duplicates removed.
Unknown options are passed to inclusive_run.py (e.g. --module-dir, --input).
"""

import argparse, hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(a, rest):
    if min(a.events, a.repeats, *a.threads) < 1:
        sys.exit("counts must be positive")
    a.output.mkdir(parents=True, exist_ok=False)
    records = []
    expected = None
    for repeat in range(a.repeats):
        for n in a.threads if repeat % 2 == 0 else a.threads[::-1]:
            dest = a.output / f"r{repeat}-w{n}"
            cmd = [
                sys.executable,
                str(HERE / "inclusive_run.py"),
                "--mode",
                "live",
                "--events",
                str(a.events),
                "--threads",
                str(n),
                "--output",
                str(dest),
                *rest,
            ]
            subprocess.run(cmd, check=True)
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


def plot(a):
    import numpy as np
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    r = json.loads(a.runs.read_text())
    threads = sorted({v["num_threads"] for v in r})
    group = {n: [v for v in r if v["num_threads"] == n] for n in threads}
    median = lambda key: np.array([np.median([v[key] for v in group[n]]) for n in threads])
    wall = median("sequencer_seconds")
    cpu = median("sequencer_cpu_seconds")
    rss = median("max_rss_MiB")
    events = r[0]["events"]
    summary = {
        str(n): {
            "wall_s": float(wall[i]),
            "cpu_s": float(cpu[i]),
            "cpu_s_per_event": float(cpu[i] / events),
            "rss_MiB": float(rss[i]),
            "speedup": float(wall[0] / wall[i]),
        }
        for i, n in enumerate(threads)
    }
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "scaling-summary.json").write_text(json.dumps(summary, indent=2))
    plt.rcParams.update({"font.size": 11, "pdf.fonttype": 42})
    with PdfPages(a.output / "scheduler_scaling.pdf") as pdf:
        fig, axs = plt.subplots(2, 2, figsize=(11.7, 8.3))
        fig.suptitle("Fatras: ACTS event-scheduler scaling")
        for ax, key, title, ylabel in [
            (axs[0, 0], "sequencer_seconds", "Elapsed time", f"Wall seconds / {events} events"),
            (axs[0, 1], "sequencer_cpu_seconds", "Total compute", f"Process CPU seconds / {events} events"),
            (axs[1, 0], "max_rss_MiB", "Peak process memory", "MiB"),
        ]:
            ax.plot(threads, median(key), "o-")
            ax.set_title(title)
            ax.set_ylabel(ylabel)
            ax.set_xlabel("ACTS workers")
            ax.set_xticks(threads)
            for n in threads:
                ax.scatter([n] * len(group[n]), [v[key] for v in group[n]], s=18, alpha=0.4)
        axs[1, 1].plot(threads, wall[0] / wall, "o-", label="Measured")
        axs[1, 1].plot(threads, threads, "--", color="grey", label="Ideal")
        axs[1, 1].set_xticks(threads)
        axs[1, 1].set_xlabel("ACTS workers")
        axs[1, 1].set_ylabel("Speedup vs one worker")
        axs[1, 1].legend()
        fig.text(
            0.035,
            0.025,
            f"Medians of {len(group[threads[0]])} repetitions; includes CSV I/O, worker setup and finalization.\nPer-event CSV hashes are identical across all runs.",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.12, 1, 0.94))
        pdf.savefig(fig)
        plt.close(fig)
    print(json.dumps(summary, indent=2))


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--output", type=Path, required=True)
    r.add_argument("--events", type=int, default=20)
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--threads", type=int, nargs="+", default=[1, 2, 4, 8])
    q = sub.add_parser("plot")
    q.add_argument("runs", type=Path)
    q.add_argument("--output", type=Path, required=True)
    a, rest = p.parse_known_args()
    if a.command == "run":
        run(a, rest)
    elif rest:
        p.error(f"unrecognized arguments: {' '.join(rest)}")
    else:
        plot(a)


if __name__ == "__main__":
    main()
