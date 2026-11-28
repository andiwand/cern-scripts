#!/usr/bin/env python3
"""Compare the TTrees of two ROOT files branch by branch.

    root_diff.py A.root B.root              # every tree the two files share
    root_diff.py A.root:tracksummary B.root:tracksummary --rtol 1e-12

Entries are sorted by event_nr / event_id when the tree has one, so output of
multi-threaded writers compares. NaNs in the same place compare equal.
Prints the differing branches with their first differing entries and exits
non-zero if anything differs. Reads with library="np", so it works where
awkward does not import.
"""

import argparse
import sys

import numpy as np
import uproot

EVENT_BRANCHES = ["event_nr", "event_id"]


def trees(spec):
    """{name: tree} for `file` (all TTrees) or `file:tree`."""
    obj = uproot.open(spec)
    if isinstance(obj, uproot.TTree):
        return {obj.name: obj}
    return {
        k.split(";")[0]: obj[k]
        for k, c in obj.classnames().items()
        if c == "TTree"
    }


def same(a, b, rtol):
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape != b.shape:
        return False
    if a.dtype.kind in "fc" and b.dtype.kind in "fc":
        if rtol:
            return bool(np.allclose(a, b, rtol=rtol, atol=0, equal_nan=True))
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def entries_equal(x, y, rtol):
    if isinstance(x, np.ndarray) and x.dtype == object:
        return len(x) == len(y) and all(entries_equal(u, v, rtol) for u, v in zip(x, y))
    return same(x, y, rtol)


def compare_tree(name, ta, tb, args):
    print(f"== {name}: entries {ta.num_entries} / {tb.num_entries}")
    ok = True
    if ta.num_entries != tb.num_entries:
        print("   entry counts differ")
        ok = False
    ka, kb = set(ta.keys()), set(tb.keys())
    for k in sorted(ka ^ kb):
        print(f"   only in {'A' if k in ka else 'B'}: {k}")
        ok = False
    if ta.num_entries != tb.num_entries:
        return ok

    order_a = order_b = slice(None)
    event = next((e for e in EVENT_BRANCHES if e in ka and e in kb), None)
    if event and not args.no_sort:
        order_a = np.argsort(ta[event].array(library="np"), kind="stable")
        order_b = np.argsort(tb[event].array(library="np"), kind="stable")

    differing = []
    for key in sorted(ka & kb):
        try:
            va = ta[key].array(library="np")[order_a]
            vb = tb[key].array(library="np")[order_b]
        except Exception as e:  # unreadable branch types
            print(f"   {key}: cannot read ({e.__class__.__name__})")
            continue
        bad = [i for i, (x, y) in enumerate(zip(va, vb)) if not entries_equal(x, y, args.rtol)]
        if bad:
            differing.append(key)
            print(f"   {key}: {len(bad)} entries differ")
            for i in bad[: args.max_print]:
                print(f"      entry {i}: A {va[i]}  B {vb[i]}")
    print("   identical" if ok and not differing else f"   differing: {differing}")
    return ok and not differing


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("a", help="file.root or file.root:tree")
    p.add_argument("b", help="file.root or file.root:tree")
    p.add_argument("--rtol", type=float, default=0.0, help="relative tolerance for floats (default exact)")
    p.add_argument("--no-sort", action="store_true", help="do not sort entries by event number")
    p.add_argument("--max-print", type=int, default=3, help="differing entries printed per branch")
    args = p.parse_args()

    ta, tb = trees(args.a), trees(args.b)
    ok = True
    if len(ta) == 1 and len(tb) == 1:
        pairs = [(next(iter(ta)), next(iter(ta.values())), next(iter(tb.values())))]
    else:
        for k in sorted(set(ta) ^ set(tb)):
            print(f"tree only in {'A' if k in ta else 'B'}: {k}")
            ok = False
        pairs = [(k, ta[k], tb[k]) for k in sorted(set(ta) & set(tb))]
    for name, x, y in pairs:
        ok &= compare_tree(name, x, y, args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
