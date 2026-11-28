#!/usr/bin/env python3
"""Compare the per-event times of an interleaved A/B run.

Reads <dir>/main_<i>/times.csv and <dir>/changed_<i>/times.csv, as written by
full_chain_perf_ab.sh, and prints the medians of each round and of all rounds.
"""

import argparse
import statistics
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("dir", type=Path, help="Output directory of the A/B run")
args = parser.parse_args()


def load(side):
    rounds = {}
    for d in sorted(args.dir.glob(f"{side}_*")):
        f = d / "times.csv"
        if f.exists():
            rounds[int(d.name.split("_")[-1])] = pd.read_csv(f)
    return rounds


main = load("main")
changed = load("changed")
rounds = sorted(set(main) & set(changed))
columns = [c for c in main[rounds[0]].columns if c in changed[rounds[0]].columns]

print(f"rounds: {rounds}")
for column in columns:
    print(f"\n== {column} [s/event, median]")
    print(f"{'round':>6} {'main':>9} {'changed':>9} {'change':>9}")
    for r in rounds:
        a = main[r][column].median()
        b = changed[r][column].median()
        print(f"{r:>6} {a:9.4f} {b:9.4f} {100 * (b / a - 1):+8.1f}%")
    a_all = pd.concat(main[r][column] for r in rounds)
    b_all = pd.concat(changed[r][column] for r in rounds)
    a = a_all.median()
    b = b_all.median()
    print(
        f"{'all':>6} {a:9.4f} {b:9.4f} {100 * (b / a - 1):+8.1f}%"
        f"   (n={len(a_all)}/{len(b_all)},"
        f" stdev {statistics.stdev(a_all):.4f}/{statistics.stdev(b_all):.4f})"
    )
