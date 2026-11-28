# CKF scattering tail on the ODD

Efficiency, fakes and resolutions of the CKF with the silicon scattering-tail
model against plain chi2 cuts, on ODD ttbar with pile-up and the Fatras
general-mixture scattering. ACTS branch `feat-ckf-scattering-tail-score`
(main plus tail PR 6572). Note:
`~/cern/notes/acts/notebook/2026-11-27_ckf-scattering-tail-score.md`.

- `run.py`: generate ODD ttbar + pile-up once; shared Fatras GeneralMixture,
  digitization and seeds; paired CKF/greedy ambiguity variants.
- `analyze.py`: truth efficiency, fake fraction, post-ambiguity score scans,
  paired event bootstrap, fit-chi2/tail-weight comparisons and pilot
  byte-equality check.
- `rates.py`: export ROOT efficiency/fake counters with PyROOT.
- `compare.py`: no/previous/new tail handling; rates versus pT/eta and
  perigee residual widths versus pT, with a common-truth cross-check.
- `plot.py`: efficiency/fake trade-off. Offline cuts do not replay finding or
  ambiguity resolution; `tail80` applies a live branch/output cut instead.
- `fitmix.py`: two-Gaussian fit to the Fatras semi-Gaussian model; prints the
  table in `Core/.../detail/ScatteringTail.hpp`. Rerun when the model changes.

Variants: `core15/core25/core49` are measurement/outlier cuts 15/25, 25/50,
49/100 per measurement dimension; `tail` is 15/25 plus the tail model;
`custom` a fixed per-slab tail fraction .03, width 5 (interface check only).
Efficiency denominator: charged truth, pT >= 1 GeV, |eta| < 3, >= 9
measurements; fakes by standard double truth matching.

## Run

In an ACTS Python environment with DD4hep, Pythia8 and ROOT:

```sh
out=~/cern/data/ckf-scattering-tail/2026-11-27_score
python run.py --output "$out/pilot" --events 2 --pu 200 \
  --variants core15 core25 tail unscored custom tail0
for pu in 200 400; do
  python run.py --output "$out/pu$pu" --events 20 --pu "$pu" \
    --variants core15 core25 core49 tail tail80
done
python rates.py "$out/pu200"
python rates.py "$out/pu400"
```

`run.py` overwrites its output directory. Analyze in a Python environment with
numpy, awkward, uproot, scipy and matplotlib. Locally that is
`ci-dependencies/.python-env/bin/python` without sourcing
`this_acts_withdeps.sh`, whose library paths break the pyarrow wheel.

```sh
python analyze.py "$out/pu200"
python compare.py "$out/pu200"
python plot.py "$out"
```

Resolution widths are half the central 68.27% / 95% residual intervals,
one matched track per truth particle, >= 30 tracks per bin. Rate errors are
68.27% Clopper-Pearson; paired differences in `summary.json` use 10,000
event-bootstrap samples. This is a Fatras occupancy stress test, not an
ITk/Geant4 occupancy match.
