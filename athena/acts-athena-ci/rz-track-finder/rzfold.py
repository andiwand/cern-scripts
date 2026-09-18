#!/usr/bin/env python3
"""Fold perf script stacks of an RZ reconstruction into a component breakdown.

usage: rzfold.py perf.data [--inline]
Shares are of the samples under ActsTrk::TrackFindingRzAlg::execute.
"""
import sys, re, collections, subprocess
data = sys.argv[1] if len(sys.argv) > 1 else "perf.data"
inline = "--inline" in sys.argv
cmd = ["perf", "script", "-i", data] + ([] if inline else ["--no-inline"]) + ["-F", "ip,sym,dso"]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
FRAME = re.compile(r"^\s+([0-9a-f]+)\s+(.*?)\s+\((.*)\)\s*$")
def short(s):
    s = re.sub(r"\(.*", "", s)
    s = s.replace("Acts::Experimental::", "").replace("ActsTrk::", "").replace("std::__cxx11::", "std::")
    return s.strip()[:120]
ALG = "TrackFindingRzAlg::execute"
# phases: first match walking from the leaf up wins
PHASES = [
    ("fillGrid", "TrackFindingRzAlg::fillGrid"),
    ("estimate", "estimateTrackParameters"),
    ("findTrack", "RzTrackFinder::findTrack"),
    ("makeTrack", "TrackFindingRzAlg::makeTrack"),
    ("duplicates", "DuplicateSeedDetector"),
    ("ensureLayout", "TrackFindingRzAlg::ensureLayout"),
    ("grid.finalize", "RzMeasurementGrid::finalize"),
    ("record/output", "WriteHandle"),
]
KEYS = [
    # findTrack internals
    "RzTrackFinder::backwardPass", "RzTrackFinder::inwardSearch", "RzTrackFinder::modulesAt",
    "RzTrackFinder::searchLayer", "RzTrackFinder::evaluate", "RzTrackFinder::update",
    "RzTrackFinder::takeKnownHit", "RzTrackFinder::placeHit", "RzTrackFinder::place",
    "RzTrackFinder::applyMaterial", "RzTrackFinder::regainEnergy", "RzTrackFinder::materialise",
    "RzTrackFinder::pathBackward", "State::moveCovariance", "StepJacobian::transport",
    "RzHelix::pathToCylinder", "RzHelix::pathToCylinderClosedForm", "RzHelix::pathToPlane", "RzHelix::pathToPerigee",
    "RzHelix::step", "stepTrig", "sincos", "__sin", "__cos", "atan2", "__log", "asin", "sqrt", "materialBandAt", "visitBins",
    "computeMultipleScatteringTheta0", "computeEnergyLoss",
    # makeTrack internals
    "toBound", "transformFreeToBoundParameters", "freeToBoundJacobian", "globalToLocal", "localToGlobal", "referenceFrame",
    "::transform", "ActsDetectorElement", "alignment", "Alignment",
    "calibrate", "allocateCalibrated", "addTrackState_impl", "appendTrackState", "calculateTrackQuantities",
    "setReferenceSurface", "setUncalibratedSourceLink", "SourceLink", "VectorMultiTrajectory", "VectorTrackContainer",
    "addTrack", "selectTrack", "dumpCandidate",
    # fillGrid internals
    "getSurfaceGeometryIdOfMeasurement", "moduleIndex", "unordered_map", "_Hashtable", "localPosition", "localCovariance",
    "identifierHash", "AuxElement", "getData", "AuxStore", "addBound", "fromBound", "RzMeasurementGrid::add",
    "MeasurementIndex", "gridOfMeasurement",
    # estimate
    "estimateTrackParameters", "estimateTrackParamsFromSeed", "intersect", "findSurface", "BoundTrackParameters",
    # allocation / memory
    "malloc", "free", "operator new", "operator delete", "memcpy", "memmove", "memset", "_int_malloc", "_int_free",
    "push_back", "_M_realloc", "vector",
]
total = 0; n_alg = 0
phase = collections.Counter()
incl = collections.Counter()
self_by_phase = collections.defaultdict(collections.Counter)
self_all = collections.Counter()
dso_by_phase = collections.defaultdict(collections.Counter)
frames = []
def flush(frames):
    global total, n_alg
    if not frames: return
    total += 1
    syms = [short(f[0]) for f in frames]
    if not any(ALG in s for s in syms): return
    n_alg += 1
    ph = "other"
    for s in syms:
        for name, key in PHASES:
            if key in s:
                ph = name; break
        if ph != "other": break
    phase[ph] += 1
    seen = set()
    for s in syms:
        for k in KEYS:
            if k in s and k not in seen:
                incl[(ph, k)] += 1; seen.add(k)
    leaf = syms[0]
    self_by_phase[ph][leaf] += 1
    self_all[leaf] += 1
    dso_by_phase[ph][frames[0][1].split("/")[-1]] += 1
for line in proc.stdout:
    if not line.strip():
        flush(frames); frames = []; continue
    m = FRAME.match(line)
    if m: frames.append((m.group(2), m.group(3)))
flush(frames)
print(f"samples {total}, under {ALG}: {n_alg} ({100*n_alg/max(1,total):.1f}% of the job)")
print("\nby phase (share of the algorithm):")
for ph, n in phase.most_common():
    print(f"  {n:7d} {100*n/max(1,n_alg):6.2f}%  {ph}")
for ph, _ in phase.most_common():
    print(f"\n=== {ph}: inclusive shares of the algorithm (nested, not additive)")
    rows = [(k, incl[(p, k)]) for (p, k) in incl if p == ph]
    for k, n in sorted(rows, key=lambda x: -x[1])[:40]:
        if n: print(f"  {n:7d} {100*n/max(1,n_alg):6.2f}%  {k}")
    print(f"--- {ph}: self by leaf symbol")
    for s, n in self_by_phase[ph].most_common(25):
        print(f"  {n:7d} {100*n/max(1,n_alg):6.2f}%  {s}")
    print(f"--- {ph}: self by dso")
    for s, n in dso_by_phase[ph].most_common(8):
        print(f"  {n:7d} {100*n/max(1,n_alg):6.2f}%  {s}")
print("\n=== whole algorithm: self by leaf symbol")
for s, n in self_all.most_common(40):
    print(f"  {n:7d} {100*n/max(1,n_alg):6.2f}%  {s}")
