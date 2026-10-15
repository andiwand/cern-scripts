"""Plot full ACTS scheduler scaling, including CSV I/O and worker initialization."""

import argparse, json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p = argparse.ArgumentParser()
p.add_argument("runs", type=Path)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
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
    fig.suptitle("File-free Fatras: full ACTS event-scheduler scaling")
    for ax, key, title, ylabel in [
        (axs[0, 0], "sequencer_seconds", "Elapsed time", "Wall seconds / 20 events"),
        (
            axs[0, 1],
            "sequencer_cpu_seconds",
            "Total compute",
            "Process CPU seconds / 20 events",
        ),
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
        "20 event indices: five unfiltered ttbar + fixed PU200 inputs repeated four times, distinct event seeds. Three repetitions.\nApple M3 Pro, 12 CPU cores, 18 GiB; includes CSV reading/writing, worker setup and finalization.\nAll 40 per-event CSV hashes match across all 12 runs. Stable pool; no Geant4 run manager or event scheduler.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.15, 1, 0.94))
    pdf.savefig(fig)
    plt.close(fig)
print(json.dumps(summary, indent=2))
