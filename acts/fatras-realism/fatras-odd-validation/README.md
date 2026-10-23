# Matched ODD Geant4 / Fatras validation

Baseline: 13 October 2026, ACTS `d41a146baacbc3a8be62cafec3a7eff37dc34f66`
on `feat/fatras-hadronic-interactions`. These are offline tools; no ACTS runtime
code changes are needed for this comparison.

This follows the synthetic-sim-validation plots: primary/secondary hit components,
particle kinematics, production vertices, r-z occupancy and hits versus eta.
It uses a newly simulated Geant4 reference with the **same current ODD geometry
and exact same generated input events** as Fatras. It does not reuse the older
ColliderML sample. All rates are absolute per event, including secondaries.
There is no digitization: these are simulation hits, not reconstructed space points.

## Sample and selections

- 20 Pythia8 ttbar events at 14 TeV, Poisson pileup with mean 200; seed 42.
- K-short and Lambda/anti-Lambda left undecayed by Pythia8 in hard scatter and
  pileup. Other generator decay settings are the ACTS helper defaults.
- Gaussian vertices: sigma x/y 0.0125 mm, sigma z 55.5 mm, time zero.
- ODD v6, revision `d70556f33b1c36abdf101a07ad8cf57eb56fbdf1`, pixels and strips;
  no calorimeter or muon system. Uniform Bz=2 T. Transport region r<1202 mm,
  |z|<4002 mm. This comparison excludes calorimeter backscatter.
- One common input filter removes particles born outside that region, neutrinos,
  exact-rest particles, p<100 MeV and charged pT<50 MeV. Supported neutral decay
  parents bypass momentum cuts. Selected inputs: 560,666 particles. The selection
  archive records every event's SHA256 and rejection counts. In particular,
  1,557 particles born outside the tracker are removed from *both* simulations.
- Geant4 11.3.2, FTFP_BERT, secondary transport and charged secondary hits enabled.
  All truth particles retained, including those without hits. Configured time kill
  at 1000 ns is applied at stepping boundaries, not a strict hit-time selection;
  a small number of later hits can remain and are counted in summary.json.
- Fatras baseline: standard EM, decays off, no nuclear table. Current Fatras:
  standard EM, native V0 decays enabled, existing pure-silicon pion/proton table.
  Both use pMin=100 MeV, pTMin=50 MeV. Decays-on retains low-momentum neutral parents;
  the EM-only variant can reject those parents by its normal pMin selection.
- Pixel plots use ACTS volumes 16,17,18; tracker_layers.pdf includes strips too.
- Generator particles have barcode generation zero; all simulation generations
  above zero are secondary. Generator-decay daughters count as generator particles.
- Inclusive hit plots use all recorded momenta. Common-acceptance plots require
  hit-entry p>=100 MeV and pT>=50 MeV; these do not equalize transport histories,
  Geant4 production cuts, or earlier secondary production.
- Particle plots require charge magnitude >0.5, production pT>100 MeV, |eta|<4,
  and at least one pixel hit. Perigee parameters use a uniform-field helix, as in
  the synthetic-simulation validation. Display windows do not renormalize counts.
- Histogram bands are event-level standard errors. Ratio bands use paired events
  with a delta-method covariance term. Empty reference bins have no ratio.
- Process labels describe the hit particle's immediate creation process, not its
  full ancestry. Nuclear includes the Geant4 hadronic-process category, not solely
  inelastic interactions; these CSVs cannot attribute nuclear hits to neutral
  versus charged incident parents. Bremsstrahlung photons make no charged hits
  themselves; downstream conversion hits appear under conversion.

## Reproduce the simulation

The local wrapper sources the existing ACTS build and supplies installed Geant4
cross-section datasets. Set ACTS_VALIDATION_BUILD and ACTS_VALIDATION_SOURCE to
use another matching build/checkout. Adjust run-env.sh's Python/data locations
when moving machines. The baseline build has ROOT, DD4hep, Geant4 and Pythia8.
Plotting uses the separate `~/cern/venv/bin/python` (numpy, pandas, matplotlib,
uproot); using it avoids conflicts with the ACTS Spack environment.

```bash
work=/tmp/odd-validation-new
mkdir -p "$work"
table="$HOME/cern/scripts/acts/fatras-realism/fatras-hadronic/data/2026-10-13/silicon-dense.table"
./run-env.sh run.py generate --output "$work/raw" --events 20 --pileup 200
~/cern/venv/bin/python filter_inputs.py "$work/raw" "$work/input"
./run-env.sh run.py geant4 --input "$work/input" --output "$work/g4" --events 20 > "$work/g4.log" 2>&1
./run-env.sh run.py fatras-em --input "$work/input" --output "$work/em" --events 20 > "$work/em.log" 2>&1
./run-env.sh run.py fatras --input "$work/input" --output "$work/fatras" --events 20 --table "$table" > "$work/fatras.log" 2>&1
~/cern/venv/bin/python material_coverage.py \
  ~/cern/build/acts/acts/dev3/_deps/odd-src/data/odd-material-maps.root \
  "$work/material-coverage.json" --table "$table"
~/cern/venv/bin/python compare.py --geant4 "$work/g4" --em "$work/em" \
  --fatras "$work/fatras" --events 20 --output "$work/plots" \
  --coverage "$work/material-coverage.json"
```

The simulation output directories must be new. Finish all requested events before
plotting. compare.py verifies matching revisions, geometry, seeds and input checksums,
unique truth barcodes and complete hit-to-particle links. It caches compact arrays,
invalidating them when the raw CSV paths, sizes or modification times change.

## Saved artifacts and replotting

`results/2026-10-13/` contains individual PDFs and the combined PDF, compact NPZ
arrays, per-event JSON counts, input selection/checksums, exact run metadata,
material-map coverage and logs. `inputs.tar.gz` preserves the exact filtered
particle CSVs. `manifest.json` records file hashes. The hadronic table remains in
`../fatras-hadronic/data/2026-10-13/silicon-dense.table`, with its SHA256 in run metadata.
Large raw simulation CSVs are not duplicated into this directory; their original
temporary locations are recorded in provenance.json. Regenerate them with the
commands above when detailed truth analysis beyond the saved arrays is needed.

Rebuild the PDFs from the archived arrays without the raw CSVs:

```bash
~/cern/venv/bin/python compare.py --cached --events 20 \
  --output results/2026-10-13 \
  --coverage results/2026-10-13/material-coverage.json
```

`--cached` explicitly trusts the archived arrays; it cannot recheck removed raw CSVs.
The input sample is selected for this validation, not an unfiltered collision sample.
No physics parameters are fitted to these events. Repeat timings in isolation before
using this run as a CPU benchmark: variants ran concurrently and CSV output dominates
some stages.

## Material coverage and reference limitations

The current silicon-only table matches effective mapped Ar/Z at relative tolerance
0.001. Only 65 of 1,060,906 positive-thickness, finite-L0 map bins match; pixel
volumes have 26 matches among 438,512 bins. These are **unweighted bin counts**,
not a track-flux-weighted interaction fraction. The actual zero nuclear-product
count in Fatras is the stronger observation. `material_coverage.py` audits the
first material channel of this single-material table; it is not a general audit
of future multi-material libraries.

Geant4 transports full volume materials; Fatras uses mapped surface materials.
Native decays cover V0s and prompt pi0, whereas Geant4 has more decay species and
channels. Consequently, residual decay or conversion discrepancies cannot be
interpreted as an isolated test of the V0 sampler. Extending table support to
ODD's effective materials is a prerequisite for a useful detector-level assessment
of added neutral-hadron projectiles; silently treating mixtures as pure silicon
would not validate the model.

The final run logs retain propagation errors and Geant4 hit-buffer warnings.
An exploratory run with `keepParticlesWithoutHits=False` hit an existing assertion
in ParticleTrackingAction; the recorded reference uses True and completes.
The time-kill threshold is step-level; inclusive plots deliberately retain any
recorded late hits. This is a baseline for subsequent physics work, not a tuned
or reconstruction-level closure claim.

## Measured baseline

Mean pixel hits per event with common hit-entry p>=100 MeV and pT>=50 MeV:

| Component | Geant4 | Fatras EM only | Fatras + native decays + Si table |
|---|---:|---:|---:|
| Generator particles | 47,191.40 | 48,482.70 | 48,504.55 |
| Simulation secondaries | 18,195.55 | 3,724.95 | 7,429.45 |
| Secondaries created by nuclear processes | 8,077.55 | 0 | 0 |

Current Fatras retains 40.83% +/- 0.42 percentage points of the reference's
secondary hits, versus 20.47% +/- 0.20 for EM-only (statistical errors).
Primary hits are 2.78% above Geant4. There are zero nuclear-created Fatras
particles, not only zero nuclear-origin hits. The immediate nuclear category
amounts numerically to about 75% of the remaining common-cut hit deficit.
This does not assign the whole deficit to an isolated hadronic model: later
conversion/decay ancestry and material differences also matter.

All 20 events finish in every variant. Current Fatras has one maximum-step
failure; EM-only has two. Neither has a no-start-volume failure after the common
input filter. Geant4 has 14 hit-buffer warnings and 77 recorded pixel hits after
the configured 1000 ns threshold. Unique truth IDs, all hit truth links, input
hashes and per-event accounting identities pass. Saved PDFs were rendered and
visually checked; the combined file contains 12 pages. See validation-checks.json.
