# Fatras charged-hadron interaction tools

Offline table generation and validation for ACTS branch
`feat/fatras-hadronic-interactions`, 2026-10-13. ACTS owns the runtime sampler and
table reader. These Geant4 calibration tools deliberately live outside ACTS.

## Generate a library

```sh
cmake -S . -B /private/tmp/fatras-table-generator \
  -DCMAKE_PREFIX_PATH=~/cern/source/acts/ci-dependencies/.spack-env/view
cmake --build /private/tmp/fatras-table-generator -j4
python3 generate.py \
  --build /private/tmp/fatras-table-generator \
  --data-root ~/cern/install/geant4/11.3.1/share/Geant4/data \
  --output /private/tmp/silicon.table
```

The defaults are G4_Si, seed 42, 512 complete interactions per node and 48
logarithmically spaced momentum nodes over 0.1–20 GeV, for pi+, pi- and protons.
The generator uses Geant4 FTFP_BERT, reads macroscopic inelastic cross sections,
normalizes them by the reference material's nuclear interaction length, and
samples conditional final states via the inelastic process. The surviving
projectile, when present, is included as a daughter. Nuclear fragments are folded
into the untransported aggregate residual system. Its four-momentum is computed
from projectile + actual target isotope minus the retained products. Local
energy deposits are also included in that aggregate. Invalid residuals fail the
run rather than silently dropping events. Null collisions are counted and
retried (zero in the recorded libraries).

Only elemental Geant4 materials are supported by this generator. Use `--material`
for another NIST element; do not use these silicon tables for arbitrary detector
mixtures. ACTS matches Ar/Z without nearest-element fallback. The generated table
contains no fitted detector hit correction.

The runtime table format and assumptions are documented in ACTS at
`docs/pages/fatras_hadronic.md`. Supplying a table is explicit opt-in:

```python
addFatras(
    sequencer, trackingGeometry, field, randomNumbers,
    pMin=0.1 * acts.UnitConstants.GeV,
    pTMin=0.05 * acts.UnitConstants.GeV,
    nuclearInteractionTable="/path/to/silicon-dense.table",
)
```

The cuts shown are validation settings, not production recommendations. The
runtime does not link Geant4. It includes native prompt pi0 -> two-photon
kinematics, while other decay channels remain a separate stack.

## Check and compare

Build an existing ACTS checkout with Fatras and integration tests, including
`ActsIntegrationTestFatrasSimulation`, with compile_commands.json enabled.

```sh
python3 build-check.py --acts-build /private/tmp/acts-atlas-review-build \
  --output /private/tmp/check-fatras-table
/private/tmp/check-fatras-table data/2026-10-13/silicon-dense.table

python3 compare.py data/2026-10-13/silicon-dense.table \
  data/2026-10-13/silicon-holdout.table --output /private/tmp/holdout.json

python3 scan.py \
  --source ~/cern/source/acts/acts/dev3 \
  --build /private/tmp/acts-atlas-review-build \
  --table data/2026-10-13/silicon-dense.table \
  --output /private/tmp/hadronic-scan \
  --events 10000 --repeats 3 --cuts 0.1 --pt-cuts 0.05
```

The checker loads the actual ACTS runtime table and tests four-momentum closure
for every event both at its reference node and between nodes. The comparison
reports rates and conditional charged multiplicity against an independently
seeded Geant4 sample; its multiplicities exclude the untransported residual and
have no transport cuts. The scan uses the ACTS test helper's four silicon layers,
2 T axial field and eight primaries per event (e-/e+, two photons, pi+/pi-, proton,
muon), with log-uniform p from 0.1 to 10 GeV, uniform eta from -1 to 1 and uniform
phi. It compares EM only to the supplied hadronic model with identical generated
inputs. Transport RNG consumption changes with enabled physics.

`scan.py` requires a new output directory. It records sources, ACTS revision/diff,
library and table checksums, compiler commands, failures and event-level timing.
Only transport calls are timed; table loading, geometry, compilation and input
generation are excluded. `--first-event` and `FATRAS_TRACE=1` help reproduce
failures; tracing invalidates timing. Daughter rejections are not separately
counted. The `nuclear_secondary_hits` count tags direct nuclear products,
including folded prompt photons; later conversions carry their own process tag.

## Recorded results

`data/2026-10-13/` contains the dense training library and an independent holdout
sample, with generator commands, checksums, dataset paths and logs. They were
generated using Geant4 11.3.2 / FTFP_BERT. The training library contains 73,728
interactions. The holdout contains 512 events per species at eight momenta
(0.15, 0.25, 0.4, 0.75, 1.5, 3.5, 7.5, 15 GeV), seed 781. Neither the data nor
this limited validation establishes a production calibration.

`results/2026-10-13/` records:

- 147,456 runtime four-momentum checks, maximum relative residual 2.09e-15.
- At the 24 holdout species/momentum points, maximum absolute relative rate
  deviation 1.19%. Conditional charged-multiplicity means differ by -9.53% to
  +5.72%; per-sample standard errors are included in the comparison JSON.
- All 25 Fatras unit-test executables and 258 integration cases pass.
- Examples C++ and Python-binding translation units pass syntax checks. The
  Python extension was not rebuilt or runtime-tested.

For the 10,000-event scan at pMin=100 MeV, pTMin=50 MeV:

| Observable | EM only | With hadronic library |
| --- | ---: | ---: |
| Simulated particles | 85895 | 88734 |
| All hits | 302863 | 304366 |
| Secondary hits | 1602 | 4223 |
| Direct nuclear secondary hits | 0 | 2614 |
| Failed particles | 0 | 0 |
| Median total transport wall time, three repeats | 1.911 s | 2.006 s |

Hadronic interactions both add daughters and terminate primaries, so the increase
in total hits is smaller than the increase in secondary hits. The roughly 5%
wall-time increase is specific to this small synthetic sample, not a production
CPU estimate. No full-detector Geant4 hit comparison has been performed.

The runtime uses a thin-surface approximation, linearly interpolated rates and
lower-node final-state shapes with CM momentum rescaling. Remaining validation
includes daughter energy/angle spectra, material mixtures and additional target
elements, backward tracks, representative events, realistic material maps, and
reconstruction observables. Unsupported species and table regions do not acquire
hadronic interactions. The table excludes fragment transport and later neutral
hadron interactions; adding those is a subsequent physics item.

Reference:
https://geant4.web.cern.ch/documentation/dev/bftd_html/ForToolkitDeveloper/GuideToExtendFunctionality/HadronicPhysics/hadronics.html
