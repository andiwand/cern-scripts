#!/usr/bin/env python3
"""Append higher-momentum bins, preserving all existing event/rate records."""
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
        assert g[0] > grid[-1]
        header[-1] = str(len(grid) + len(g))
        newbody = body + b
        assert newbody[: len(body)] == body
        checks[key[0]] = {
            "old_range": [grid[0], grid[-1]],
            "new_range": [grid[0], g[-1]],
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
