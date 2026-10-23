#!/usr/bin/env python3
"""Compare two propagation summary files branch by branch.

Use it to prove that a navigation change leaves the propagation unchanged.
awkward is unusable in this environment, so read with library="np".
"""

import argparse

import numpy as np
import uproot


def branchesEqual(before, after):
    if len(before) != len(after):
        return False
    for x, y in zip(before, after):
        if np.ndim(x) == 0:
            if x != y:
                return False
        elif len(x) != len(y) or not np.array_equal(np.asarray(x), np.asarray(y)):
            return False
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("before")
    p.add_argument("after")
    args = p.parse_args()

    a = uproot.open(args.before)
    b = uproot.open(args.after)
    treeName = a.keys()[0]
    ta, tb = a[treeName], b[treeName]

    differing = [
        br
        for br in ta.keys()
        if not branchesEqual(
            ta[br].array(library="np"), tb[br].array(library="np")
        )
    ]

    print(f"tree={treeName} entries={ta.num_entries} branches={len(ta.keys())}")
    print("identical" if not differing else f"differing branches: {differing}")
    raise SystemExit(1 if differing else 0)


if __name__ == "__main__":
    main()
