#!/usr/bin/env python3
"""Extend channels of BASE with the bins of EXTENSION, preserving all records.

Each extended channel's new bins must lie entirely above (appended) or below
(prepended) the base momentum grid. Writes OUTPUT and OUTPUT.json with checks.
"""
import argparse, hashlib, json
from pathlib import Path


def channels(path):
    lines = [x for x in path.read_text().splitlines(keepends=True) if x.strip()]
    assert lines[0].strip() == "ACTS_FATRAS_NUCLEAR_V1"
    out = {}
    i = 2
    for _ in range(int(lines[1])):
        header = lines[i].split()
        i += 1
        start = i
        grid = []
        for _ in range(int(header[-1])):
            p, rate, n = lines[i].split()
            grid.append(float(p))
            i += 1
            for _ in range(int(n)):
                products = int(lines[i].split()[-1])
                i += 1 + products
        key = tuple(header[:4])
        assert key not in out
        out[key] = (header, "".join(lines[start:i]), grid)
    assert i == len(lines)
    return out


p = argparse.ArgumentParser(description=__doc__)
p.add_argument("base", type=Path)
p.add_argument("extension", type=Path)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
base = channels(a.base)
extra = channels(a.extension)
assert extra.keys() <= base.keys()
result = ["ACTS_FATRAS_NUCLEAR_V1\n", str(len(base)) + "\n"]
checks = {}
for key, (header, body, grid) in base.items():
    if key in extra:
        h, b, g = extra[key]
        header[-1] = str(len(grid) + len(g))
        if g[0] > grid[-1]:
            newbody = body + b
            assert newbody[: len(body)] == body
        else:
            assert g[-1] < grid[0], f"overlapping momentum grids for {key}"
            newbody = b + body
            assert newbody[-len(body) :] == body
        checks[key[0]] = {
            "old_range": [grid[0], grid[-1]],
            "new_range": [min(grid[0], g[0]), max(grid[-1], g[-1])],
            "old_bin_records_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "old_bins_unchanged": True,
        }
    else:
        newbody = body
    result += [" ".join(header) + "\n", newbody]
a.output.write_text("".join(result))
meta = {
    "inputs": {
        str(f): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in [a.base, a.extension]
    },
    "extensions": checks,
    "table_sha256": hashlib.sha256(a.output.read_bytes()).hexdigest(),
}
a.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
