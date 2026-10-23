# Native Fatras decay validation

2026-10-13, ACTS branch `feat/fatras-hadronic-interactions`.

- `c9d82eba25`: native decay model, shared two-body kinematics, selection, truth and tests.
- `d41a146baa`: opt-in Examples/Python configuration and documentation.

The runtime is in ACTS (`docs/pages/fatras_decays.md`). These scripts only build
and run synthetic validation. They need an ACTS build with Fatras, integration
tests and `compile_commands.json`; no Geant4 runtime is needed. An optional
hadronic table is the same input for both decay settings.

```sh
python3 scan.py \
  --source ~/cern/source/acts/acts/dev3 \
  --build /private/tmp/acts-atlas-review-build \
  --output /private/tmp/native-v0-new \
  --events 10000 --repeats 3 --cuts 0.1 --pt-cuts 0.05 --v0-only

python3 scan.py \
  --source ~/cern/source/acts/acts/dev3 \
  --build /private/tmp/acts-atlas-review-build \
  --output /private/tmp/native-mixed-new \
  --events 10000 --repeats 3 --cuts 0.1 --pt-cuts 0.05 \
  --table ~/cern/scripts/acts/fatras-hadronic/data/2026-10-13/silicon-dense.table
```

Use a new output directory. The scanner records per-layer hits, decay/process
counts, failed particles, timing, source/library checksums, build commands and
configuration. Sources and stdout/stderr summaries are archived under
`results/2026-10-13/`. `implementation.patch` and `commits.txt` identify the
final committed implementation. Scan metadata records the earlier working-tree
revision; the scans precede commits and formatting, with the same physics code.

Both samples use the four-layer silicon test geometry, 2 T axial field, uniform
eta in [-1,1], uniform azimuth, pMin=100 MeV, pTMin=50 MeV, seed 42 and three
repetitions in shuffled order. The generated inputs and event seeds are identical
between settings; enabling decays changes transport RNG consumption. Only
transport calls are timed, excluding input generation, geometry and table loading.

The V0 sample has one K-short, Lambda and anti-Lambda per event, log-uniform
momentum 0.001–10 GeV. With decays disabled, pMin rejects 15,176 of 30,000 inputs;
with decays enabled, all moving decay parents are retained. This comparison
therefore includes the intended change to parent acceptance.

The mixed sample has e-/e+, two photons, pi+/pi-, proton, muon and the three V0s
per event, log-uniform momentum 0.1–10 GeV. It uses the silicon hadronic table
from the first physics stack in both settings. No input is rejected.

| Sample, 10,000 events | Decays disabled | Native decays |
| --- | ---: | ---: |
| V0: propagated particles | 14824 | 93179 |
| V0: secondary hits | 0 | 92227 |
| V0: failed particles | 0 | 0 |
| V0: median total transport time | 0.0750 s | 0.5927 s |
| Mixed: propagated particles | 118734 | 185044 |
| Mixed: secondary hits | 4223 | 113414 |
| Mixed: all hits | 304366 | 413551 |
| Mixed: failed particles | 0 | 0 |
| Mixed: median total transport time | 2.1301 s | 2.6743 s |

All counts reproduce across the three repetitions. Mixed-sample transport cost
increases by about 26%. These deliberately V0-rich samples do not estimate
collision-event occupancy or production CPU, and no full-detector Geant4 hit
comparison is made. Daughter rejections and production-level cut losses are not
separately counted.

Validation logs also record:

- 26 Fatras unit-test executables pass.
- 260 integration cases / 26,298 assertions pass.
- Native unit tests sample 100,000 lifetimes and 100,000 decay channels for each
  of K-short, Lambda and anti-Lambda. They test lifetime means/survival, channel
  fractions, isotropy, conservation, boosts and replay.
- Integration tests check decay space-time positions over four momenta per
  species, world exit, low-momentum neutral acceptance, cascade ancestry and hits.
- Required pre-commit checks pass. Examples C++ and both changed binding
  translation units pass syntax checks; the Python extension is not rebuilt or
  runtime-tested.

The physics scope deliberately omits rare modes, polarization, mixing,
regeneration and at-rest transport. Retained V0 channel weights are normalized;
pi0 uses only gamma gamma. Neutral hadron interactions remain a separate item.
