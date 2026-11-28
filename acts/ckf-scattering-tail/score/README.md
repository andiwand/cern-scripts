# ODD cumulative scattering-tail score

Note: `~/cern/notes/acts/notebook/2026-11-27_ckf-scattering-tail-score.md`.
ACTS branch: `feat-ckf-scattering-tail-score` (current main plus tail PR 6572).

- `run.py`: generate ODD ttbar + pileup once; shared Fatras GeneralMixture,
  digitization and seeds; paired CKF/greedy ambiguity variants.
- `analyze.py`: truth efficiency, fake fraction, post-ambiguity score scans,
  paired event bootstrap, fit-chi2/tail-weight comparisons and pilot byte-equality check.
- `rates.py`: export ROOT efficiency/fake counters with PyROOT.
- `compare.py`: explicit no/previous/new handling; rates versus pT/eta and
  perigee residual widths versus pT, with a common-truth cross-check.
- `plot.py`: efficiency/fake tradeoff. Offline cuts do not replay finding or
  ambiguity resolution. `tail80` applies a live branch/output cut instead.
- `core15/core25/core49`: measurement/outlier cuts 15/25, 25/50, 49/100
  per measurement dimension. `tail` uses 15/25 plus the silicon tail model.
  `custom`: fixed per-slab tail fraction .03, width 5 (interface check only).
- Efficiency denominator: charged truth, pT ≥ 1 GeV, |eta| < 3, ≥ 9 measurements.
  Fake classification: standard double truth matching. All variants use the
  same denominator. Occupancy includes empty sensitive modules.

Run in an ACTS Python environment with DD4hep, Pythia8 and ROOT:

```sh
artifact_dir=~/cern/notes/acts/notebook/2026-11-27_ckf-scattering-tail-score
python run.py --output "$artifact_dir/pilot" --events 2 --pu 200 \
  --variants core15 core25 tail unscored custom tail0
for pu in 200 400; do
  python run.py --output "$artifact_dir/pu$pu" --events 20 --pu "$pu" \
    --variants core15 core25 core49 tail tail80
done
```

Export rates in the ACTS/ROOT environment:

```sh
python rates.py "$artifact_dir/pu200"
python rates.py "$artifact_dir/pu400"
```

Analyze in a Python environment with numpy, awkward, uproot, scipy and matplotlib.
On the local setup, use `ci-dependencies/.python-env/bin/python` without sourcing
`this_acts_withdeps.sh`: its library paths conflict with the pyarrow wheel.

```sh
python analyze.py "$artifact_dir/pilot"
python analyze.py "$artifact_dir/pu200"
python analyze.py "$artifact_dir/pu400"
python plot.py "$artifact_dir"
python compare.py "$artifact_dir/pu200"
python compare.py "$artifact_dir/pu400"
```

The run overwrites its own output directory. Logs, ROOT files, JSON diagnostics,
summaries and plots belong in the note's companion artifact directory.
This is a Fatras occupancy stress test, not an ITk/Geant4 occupancy match.

Resolution widths are half the central 68.27% / 95% residual intervals; no
Gaussian fit. Curves use one matched track per selected truth particle and
require ≥30 tracks per bin. `resolutions.json` also records a common-truth
comparison, to separate fit changes from changes in which particles are recovered.
No per-mode cut optimization is claimed; further tuning should use separate data.
Rate error bars are 68.27% Clopper–Pearson intervals; overall paired differences
in `summary.json` use 10,000 event-bootstrap samples and 95% intervals.
