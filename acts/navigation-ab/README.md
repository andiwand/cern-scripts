# Navigation A/B on the ODD

Checks that a change to the navigator leaves the propagation unchanged, for
Gen1 and Gen3 separately. `nav_fingerprint.py` runs the straight-line
propagator over the ODD and writes the propagation summary;
`../../root/root_diff.py` then diffs two of them branch by branch, so a single
changed surface or path length shows up.

## Use

In an ACTS environment (`source ~/cern/source/acts/acts/<clone>/activate.sh`):

1. Build the baseline, then run both generations:

       python nav_fingerprint.py --geo-mode gen1 -n 20 --tracks 20 -o before_gen1.root
       python nav_fingerprint.py --geo-mode gen3 -n 20 --tracks 20 -o before_gen3.root

2. Build the change and repeat with `after_*.root`.
3. Diff; exits non-zero if any branch differs:

       python ../../root/root_diff.py before_gen1.root after_gen1.root
       python ../../root/root_diff.py before_gen3.root after_gen3.root

20 events x 20 tracks (400 tracks) are enough to catch a navigation change and
take about 2 s per generation.

## Traps

- `Examples/Scripts/Python/propagation_validation.py` cannot write its summary,
  because it misses `import acts.examples.root`. That is why this runner exists.
- `library="ak"` fails in the spack environment: awkward pulls in pyarrow, whose
  `libarrow` cannot find `_iconv`. `root_diff.py` reads with `library="np"`.
