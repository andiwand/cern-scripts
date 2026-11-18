#!/usr/bin/env python3
"""Fold a macOS `sample` call tree into stacks and attribute the CKF time.

Usage: fold_sample.py sample.txt [--root REGEX]
Prints inclusive shares (each stack counted once per category) of the
subtree below the last frame matching --root.
"""
import re
import sys
import argparse
from collections import defaultdict

LINE = re.compile(r"^([\s+!:|]*)(\d+)\s+(.*?)\s+\(in ([^)]*)\)")
LINE2 = re.compile(r"^([\s+!:|]*)(\d+)\s+(.*)$")

CATEGORIES = [
    ("mixture chi2 (selectWithTail)", r"selectWithTail|calculateMixtureChi2|mixtureChi2|calculateChi2AndLogDet"),
    ("creator with tail", r"createTrackStatesWithTail"),
    ("core creator (createTrackStates)", r"TrackStateCreator::createTrackStates$|TrackStateCreator::calibrateCandidates"),
    ("measurement select (core)", r"MeasurementSelector::select$|MeasurementSelector::selectImpl|calculateChi2$"),
    ("calibration", r"calibrate"),
    ("makeTrackState / copy", r"addTrackState_impl|makeTrackState|copyFrom|shareFrom"),
    ("tail transport/add", r"ScatteringTailState::"),
    ("evaluateMaterialSlab", r"evaluateMaterialSlab"),
    ("material interaction", r"performMaterialInteraction"),
    ("navigation", r"Navigator::(nextTarget|initialize|handleSurfaceReached)|resolveSurfaces|resolveLayers"),
    ("stepper step", r"Stepper::step$|sympyStep$"),
    ("covariance transport", r"transportCovarianceToBound|boundState\b|transportCovariance|boundToBoundTransportJacobian"),
    ("kalman update", r"GainMatrixUpdater"),
    ("smoothing", r"Smoother::|::smooth"),
    ("branch stopper / track ops", r"branchStopper|BranchStopper|TrackSelector"),
    ("malloc/free/memmove", r"^(_?malloc|_?free|operator new|operator delete|_platform_memmove|_platform_memset|.*szone|.*nanov2|_xzm)"),
]


def bare(name):
    """function name without template arguments and parameters"""
    out, depth, i = [], 0, 0
    # cut the parameter list: the first '(' at template depth 0
    for c in name:
        if c == "<":
            depth += 1
            continue
        if c == ">":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            if c == "(" and out and not "".join(out).endswith("operator"):
                break
            out.append(c)
    return "".join(out)


def parse(path):
    stacks = defaultdict(int)
    stack = []  # (indent, name, count)
    for raw in open(path, errors="replace"):
        if not raw.strip():
            continue
        m = LINE.match(raw) or LINE2.match(raw)
        if not m or not raw.lstrip(" +!:|").strip()[0].isdigit():
            continue
        indent = len(m.group(1))
        count = int(m.group(2))
        name = m.group(3).strip()
        while stack and stack[-1][0] >= indent:
            ind, nm, cnt, child = stack.pop()
            self_ = cnt - child
            if self_ > 0:
                stacks[tuple(s[1] for s in stack) + (nm,)] += self_
        if stack:
            stack[-1][3] += count
        stack.append([indent, name, count, 0])
    while stack:
        ind, nm, cnt, child = stack.pop()
        self_ = cnt - child
        if self_ > 0:
            stacks[tuple(s[1] for s in stack) + (nm,)] += self_
    return stacks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample")
    ap.add_argument("--root", default=r"TrackFindingAlgorithm::execute")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--within", help="also list the leaves below frames matching this")
    a = ap.parse_args()
    root = re.compile(a.root)
    stacks = parse(a.sample)
    total = 0
    cat = defaultdict(int)
    leaf = defaultdict(int)
    cats = [(n, re.compile(p)) for n, p in CATEGORIES]
    within_total = [0]
    within_child = defaultdict(int)
    within_leaf = defaultdict(int)
    for st, w in stacks.items():
        idx = [i for i, f in enumerate(st) if root.search(f)]
        if not idx:
            continue
        sub = st[idx[-1] + 1 :]
        subBare = [bare(f) for f in sub]
        total += w
        for n, rx in cats:
            if any(rx.search(f) for f in subBare):
                cat[n] += w
        leaf[sub[-1] if sub else st[-1]] += w
        if a.within:
            wi = [i for i, f in enumerate(subBare) if re.search(a.within, f)]
            if wi:
                within_total[0] += w
                # the frame directly below the matched one, and the leaf
                nxt = subBare[wi[0] + 1] if wi[0] + 1 < len(subBare) else "<self>"
                within_child[nxt] += w
                within_leaf[subBare[-1]] += w
    print(f"samples below root: {total}")
    for n, _ in CATEGORIES:
        print(f"  {100 * cat[n] / total:6.2f} %  {n}")
    if a.within:
        print(f"below {a.within}: {100 * within_total[0] / total:.2f} %")
        print(" direct children:")
        for f, w in sorted(within_child.items(), key=lambda x: -x[1])[:15]:
            print(f"  {100 * w / total:6.2f} %  {f[:140]}")
        print(" leaves:")
        for f, w in sorted(within_leaf.items(), key=lambda x: -x[1])[:15]:
            print(f"  {100 * w / total:6.2f} %  {f[:140]}")
    print("top leaf functions:")
    for f, w in sorted(leaf.items(), key=lambda x: -x[1])[: a.top]:
        print(f"  {100 * w / total:6.2f} %  {f[:150]}")


main()
