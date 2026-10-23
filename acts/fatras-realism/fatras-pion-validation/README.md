# Charged-pion validation and ODD beam-pipe correction

Study dated 14 October 2026, on ACTS `feat/fatras-hadronic-interactions`.
This separates pion momentum coverage, interaction frequency, conditional daughter
yield and material-map coverage. No pion rate or multiplicity is fitted to ODD.

Two corrections are provided as external input files:

- Extend the pi+/pi− reference libraries above 20 GeV/c to approximately 7 TeV/c,
  preserving every previous momentum-bin record and every other channel.
- Fill the 1152 empty bins of the known 0.8 mm ODD beryllium beam pipe. The old map
  has material only in its two central z bins (roughly |z|<800 mm), although the
  physical cylinder extends to |z|=4000 mm. All sampled central bins and every
  other histogram value and axis remain unchanged.

Both are optional inputs; the original tables and ODD material map are retained.
The ACTS runtime has no new Geant4 dependency. The only ACTS code addition for
this study is an optional Geant4 stepping-action factory, used by the external
recorder. Results/PDFs are in `results/2026-10-14/`; inputs are in
`data/2026-10-14/`. Large generated artifacts are not version-controlled.

## Build the external diagnostics

```
python3 build-diagnostics.py --acts-build /path/to/acts/build \
  --output "$PWD/pion_diagnostics.so"
python3 build-sampler.py --acts-build /path/to/acts/build \
  --output "$PWD/sample-collisions"
```

The build helpers reuse the ACTS compile database. The diagnostic module helper
currently uses this workstation's macOS Geant4 library paths. Runtime Python
must match the ACTS bindings (here Python 3.14); the environment wrapper in
`../fatras-neutral-hadrons/odd/run-env.sh` configures this installation.

`diagnostics.cpp` supplies a read-only Geant4 step observer and a pion initial/
final-state writer. The observer records actual step locations, incident
**pre-step** momentum, process subtype, material and accumulated nuclear lengths.
Pre-step momentum is after earlier transport, but does not resolve continuous
energy loss within the interaction-ending step. Raw step-secondary counts can
include along-step products; analysis instead uses truth creation processes and
vertex matching to obtain nuclear-only yields. No random numbers are consumed.

`run.py` uses the same generator input, geometry, field, transport settings and
silicon sensitive-volume mapping as the previous ODD study. Geant4 writes compact
pion diagnostics and hit CSVs; its existing full truth CSVs may be reused **only
after checking all hit files match**, including truth barcodes. Fatras writes its
own full particle/hit CSVs and pion final states. The baseline Fatras replay and
all 20 Geant4 hit files are checked against the previous run.

```
bash ../fatras-neutral-hadrons/odd/run-env.sh run.py fatras \
  --input /path/to/identical-selected-inputs --output /tmp/pion-test --events 20 \
  --table data/2026-10-14/silicon-pion-extended.table --reference-material \
  --material-map data/2026-10-14/odd-material-beampipe.root
```

Omit `--material-map` for the original map. Use the previous table for the
coverage control. Mode `geant4` uses the table only as a diagnostic rate reference;
it does not alter Geant4 physics. Same pMin=100 MeV, charged pTMin=50 MeV,
neutral KE=10 MeV, neutral global-time cutoff=1000 ns and native V0 decays as before.

## Calibration and map recipe

`calibrate.py` invokes the existing external FTFP_BERT generator, with 52 added
logarithmic nodes/species, 512 events/node and seed 8342. Independent midpoint
samples use 256 events/point and seed 9242. The original 0.1–20 GeV/c bins remain
unchanged. Supply `--base-table`, `--generator-build`, `--data-root`, `--output`,
and optionally `--check` pointing to the existing ACTS table-conservation checker.
`extend-table.py` rejects overlaps and mismatched channel definitions and writes
checksums of preserved records. This is calibrated coverage, not extrapolation.

`material-constants.py --output beryllium.json`, under the ACTS runtime wrapper,
exports Geant4 NIST Be constants. These match the ODD material: density 1.848 g/cm3,
A=9.01218, Z=4, X0=352.75975 mm and L0=394.13294 mm. The latter is also checked
against the actual material in the Geant4 step records.

```
python repair-beampipe-map.py --input /path/to/ODD/data/odd-material-maps.root \
  --constants beryllium.json --output odd-material-beampipe.root
```

This recipe checks the ODD XML dimensions, expected binning and empty-bin pattern.
It modifies only the known beam-pipe surface. Outer bins are weighted by physical
z overlap to account for the map's 1 mm envelope. It is not a generic procedure
for filling empty bins, and it does not assume that empty bins elsewhere contain
material. The original ODD file is never overwritten. The map should ultimately
be corrected/regenerated in the ODD material-data workflow.

## Analysis and PDFs

- `analyse-pions.py`: associate nuclear daughters and common-cut pixel hits to
  interaction vertices. Explicit categories separate table coverage, transport
  cuts, fragments, elastic scattering, capture and unmatched vertices. Fatras
  nuclear parents have outcome KilledInteraction **and nonzero final momentum**;
  EM-stopped pions are excluded. Thirty G4 hits in this sample have no matched
  vertex and are kept explicit. The 0.5 micron space/ct matching tolerance and
  ambiguity checks are in the script.
- `sample-collisions TABLE G4_DIAGNOSTIC_DIR OUTPUT_DIR EVENTS TRIALS`: sample the
  reference library at each measured G4 collision's incident momentum and
  direction; this study uses 64 trials and independent event seeds. Conditional
  accepted multiplicity includes surviving leading pions, excludes fragments,
  and applies production p/pT cuts. It is not a downstream hit prediction.
- `compare.py`: previous ODD distribution suite, with explicit
  `--allow-material-map-change` for the map ablation. All other geometry, field,
  input hash and event checks remain. The override is recorded and visible on
  the summary page. `--cached` regenerates plots from archived NPZ arrays.
- `plot-pions.py`: four-page PDF covering interaction momentum, primary-pion
  interaction fractions, hit attribution, conditional yields, beam-pipe map and
  vertex coverage, and independent high-momentum calibration checks.

Geant4's world/time kills are checked at steps, and material exposure can include
an overshooting last step. Interaction fractions include decay, transport and
material differences; they are not standalone cross-section measurements.
Geant4 volume material and Fatras surface slabs remain different approximations.
The Si reference library is still used for final states, including on Be.
Nuclear fragments, at-rest capture, charged-pion decays and several projectile
species remain outside the current Fatras model. Do not tune rates to compensate
for those omissions. Timings include diagnostics and CSV I/O; table loading is
reported separately.

The shared observer also accepts `--projectiles PDG...` and
`--diagnostic-prefix NAME`; defaults preserve the original pion outputs.
For example `--projectiles -2212 -2112 --diagnostic-prefix antinucleon` reuses
these tools for antinucleon studies. Missing calibration channels give zero
reference hazard, not a failure of Geant4 recording. Event files are opened
before filtering species, so an event without the selected hadrons still has
empty diagnostic headers. Source revision, working-tree status and diff hash
are recorded in simulation metadata. The plotter delegates to the shared ODD
implementation in `../fatras-neutral-hadrons/odd/compare.py`.
