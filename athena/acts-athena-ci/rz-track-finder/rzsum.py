#!/usr/bin/env python3
"""CKF vs RZ track finding, normalised to a control algorithm identical in both."""
import re, sys, glob, os, statistics
PAT = re.compile(r"PerfMonMTSvc\s+INFO Execute\s+(\d+)\s+([0-9.]+)\s+\S+\s+\S+\s+(\S+)\s*$")
# the finder is a different algorithm on each side, so match by suffix
# anchored, so that ActsLargeRadiusTrackFindingAlg (the CKF in both
# configurations, since the RZ finder runs on the primary pass only) is
# not mistaken for the algorithm under test
TARGET = {"ckf": re.compile(r"^ActsTrackFindingAlg$"),
          "rz": re.compile(r"^ActsTrackFindingRzAlg$")}
CONTROL = os.environ.get("CONTROL", "ActsPixelClusterizationAlg")

def read(logfile):
    out = {}
    with open(logfile, errors="replace") as f:
        for line in f:
            m = PAT.search(line.rstrip())
            if m:
                out[m.group(3)] = (int(m.group(1)), float(m.group(2)))
    return out

SEEDS = {
    # the CKF skips duplicate seeds and only runs on the rest; the RZ finder
    # runs on every one, so the per-seed cost is what compares them
    "ckf": re.compile(r"\|\s*Used\s+seeds\s*\|\s*(\d+)"),
    "rz": re.compile(r"RZ track finding:\s*(\d+) seeds"),
}
SEEDS_IN = re.compile(r"\|\s*Input seeds\s*\|\s*(\d+)")


DUPES = re.compile(r"(\d+) duplicate seeds skipped")


def seeds(logfile, variant):
    """Seeds the finder actually ran on, and the seeds it was offered.

    The CKF's table reports the two directly. The RZ finalize line reports the
    seeds offered and how many of them deduplication skipped, so the seeds it
    ran on is the difference.
    """
    used = offered = dupes = None
    with open(logfile, errors="replace") as f:
        for line in f:
            if used is None:
                m = SEEDS[variant].search(line)
                if m:
                    used = int(m.group(1))
            if offered is None:
                m = SEEDS_IN.search(line)
                if m:
                    offered = int(m.group(1))
            if variant == "rz" and dupes is None:
                m = DUPES.search(line)
                if m:
                    dupes = int(m.group(1))
    if variant == "rz" and used is not None:
        offered = used
        used = used - (dupes or 0)
    return used, (offered if offered is not None else used)


def pick(rows, pattern):
    hits = [(k, v) for k, v in rows.items() if pattern.search(k)]
    return hits[0][1] if len(hits) == 1 else None

tag = sys.argv[1] if len(sys.argv) > 1 else "r"
# job directories live in the acts-athena-ci run area, not next to this script
base = os.environ.get("ACI_RUN", "/home/astefl/source/acts/acts-athena-ci/run")
res = {}
for v in ("ckf", "rz"):
    rows = []
    for d in sorted(glob.glob(os.path.join(base, f"{tag}_{v}_*"))):
        log = os.path.join(d, "log.RAWtoALL")
        if not os.path.exists(log):
            continue
        r = read(log)
        t = pick(r, TARGET[v])
        if t is not None and CONTROL in r:
            used, offered = seeds(log, v)
            rows.append((os.path.basename(d), t[1], r[CONTROL][1], used,
                         offered))
    res[v] = rows

for v in ("ckf", "rz"):
    print(f"=== {v}")
    for name, t, c, used, offered in res[v]:
        per = f"  {1e3*t/used:7.1f} us/seed" if used else ""
        print(f"  {name:20s} finder={t:9.2f}  {CONTROL}={c:9.2f}"
              f"  ratio={t/c:.4f}{per}")
    if res[v]:
        raw = [t for _, t, _, _, _ in res[v]]
        rat = [t / c for _, t, c, _, _ in res[v]]
        us = [u for _, _, _, u, _ in res[v] if u]
        off = [o for _, _, _, _, o in res[v] if o]
        if us:
            print(f"  seeds run on = {statistics.mean(us):.0f}"
                  f" of {statistics.mean(off):.0f} offered")
        print(f"  mean raw = {statistics.mean(raw):9.2f} ms"
              + (f" sd={statistics.stdev(raw):6.2f} ({100*statistics.stdev(raw)/statistics.mean(raw):.1f}%)" if len(raw) > 1 else ""))
        print(f"  mean norm= {statistics.mean(rat):9.5f}"
              + (f" sd={statistics.stdev(rat):8.5f} ({100*statistics.stdev(rat)/statistics.mean(rat):.1f}%)" if len(rat) > 1 else ""))

if res["ckf"] and res["rz"]:
    nk = statistics.mean([t / c for _, t, c, _, _ in res["ckf"]])
    nr = statistics.mean([t / c for _, t, c, _, _ in res["rz"]])
    rk = statistics.mean([t for _, t, _, _, _ in res["ckf"]])
    rr = statistics.mean([t for _, t, _, _, _ in res["rz"]])
    print(f"\nRZ vs CKF: normalised {100*(nr/nk-1):+.1f}%   raw {100*(rr/rk-1):+.1f}%")
    uk = [u for _, _, _, u, _ in res["ckf"] if u]
    ur = [u for _, _, _, u, _ in res["rz"] if u]
    if uk and ur:
        pk = statistics.mean([1e3 * t / u for _, t, _, u, _ in res["ckf"] if u])
        pr = statistics.mean([1e3 * t / u for _, t, _, u, _ in res["rz"] if u])
        print(f"per seed the finder ran on: ckf {pk:.1f} us, rz {pr:.1f} us"
              f"  ({100*(pr/pk-1):+.1f}%)")
        print("note: the CKF skips duplicate seeds, the RZ finder does not,"
              " so the totals above are over different seed counts")
