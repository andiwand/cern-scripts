# Navigation A/B on the ODD

Proves that a change to the navigator leaves the propagation unchanged, for
Gen1 and Gen3 separately. Behind the external-surface work on `acts` (PR that
introduces `Acts::ExternalSurface`).

The straight-line propagator runs over the ODD and `nav_fingerprint.py` writes
a propagation summary. `compare.py` then diffs the two files branch by branch,
so a single changed surface or path length shows up.

## Use

1. Build the baseline, then run both generations:

       python nav_fingerprint.py --geo-mode gen1 -n 20 --tracks 20 -o before_gen1.root
       python nav_fingerprint.py --geo-mode gen3 -n 20 --tracks 20 -o before_gen3.root

2. Build the change and repeat with `after_*.root`.
3. Diff:

       python compare.py before_gen1.root after_gen1.root
       python compare.py before_gen3.root after_gen3.root

`compare.py` exits non-zero if any branch differs.

## Traps

- `source ~/cern/source/acts/acts/dev3/activate.sh` first, so the ODD and the
  python bindings are on the path.
- `Examples/Scripts/Python/propagation_validation.py` cannot write its summary,
  because it misses `import acts.examples.root`. That is why this runner exists.
- `library="ak"` fails in this environment: awkward pulls in pyarrow, whose
  `libarrow` cannot find `_iconv`. Read with `library="np"`.
- 20 events x 20 tracks gives 400 tracks, which is enough to catch a
  navigation change and runs in about 2 s per generation.
