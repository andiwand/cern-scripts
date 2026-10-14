# Fatras neutral-hadron calibration and ODD validation

External tools for neutron and K-long inelastic interactions. ACTS runtime uses
an immutable correlated-event table and does not depend on Geant4. These tools
are intentionally outside ACTS; no RootNuclearInteractionParametersWriter is used.

## Calibration

`generate.cpp` builds against Geant4 (CMake), extracts FTFP_BERT inelastic rates
and correlated final states for explicitly selected projectile PDGs. It supports
an elemental reference target. Nuclear fragments and local deposits are included
in an untransported aggregate remnant. Leading projectiles are retained. Null
collisions are counted and retried, not stored as interactions. The rate is the
macroscopic inelastic cross section times Geant4's reference nuclear length.

```
cmake -S . -B /tmp/fatras-tables -DGeant4_DIR=/path/to/lib/cmake/Geant4
cmake --build /tmp/fatras-tables
python3 generate.py --build /tmp/fatras-tables --data-root /path/to/Geant4/data \
  --output neutron-kl.table --projectiles 2112 130 --seed 1942 --events 512
```

Default grid: 48 logarithmic nodes, 0.1–20 GeV/c, silicon. Use independent seeds
for a holdout at the same nodes and at geometric midpoints. `compare.py` compares
rates and charged multiplicity before transport cuts; it does not validate all
kinematic correlations. `plot-calibration.py` plots the JSON comparisons.

`combine.py INPUT... --output combined.table` preserves input channel bodies
verbatim and writes checksums. Channels must be disjoint. Validate the combined
table with the real ACTS parser and runtime sampler:

```
python3 build-check.py --acts-build /path/to/acts/build --output /tmp/check-table
/tmp/check-table combined.table
```

The loader validates charge and four-momentum; the checker resamples every event
at its node and next midpoint in a rotated lab frame. Calibration files and
manifests for this study are in `data/2026-10-14/` (not version-controlled).

## ODD comparison

`odd/run-env.sh` is a workstation environment wrapper; adjust its local paths
when moving machines. `odd/run.py` configures the ODD tracker only, constant 2 T,
Geant4 FTFP_BERT or Fatras with native V0 decays, local-L0 reference-material
interactions, pMin=100 MeV and charged pTMin=50 MeV. It reads previously selected
CSV inputs. Do not regenerate different inputs for different simulators.

```
bash odd/run-env.sh odd/run.py fatras --input /path/to/selected-inputs \
  --output /tmp/odd-neutral --events 20 --table combined.table --reference-material
```

Use `--no-neutral-hadrons` for the charged-only control. Vary
`--neutral-ke-min` (GeV; default .010) independently of charged p/pT cuts.
`--neutral-time-max` is in ns (default 1000, checked at steps). Tables have finite
momentum support: a zero energy cut does not supply missing thermal-neutron or
at-rest physics. Inputs for this study already exclude p<100 MeV/c.

`odd/compare.py` checks matching geometry, field, seeds, input hashes and events;
it produces an 11-page PDF and separate plots of pixel hits, spectra, origins,
RZ occupancy, and tracker layers. `--allow-different-revisions` is explicit when
reusing the archived Geant4 sample. `--cached` replots saved NPZ files without CSV.

`odd/ancestry.py` requires the new optional parent columns in particle CSVs. It
counts immediate nuclear-parent species and immediate decay/conversion parent
PDGs for common-cut pixel hits. Unresolved IDs remain explicit. It does not
reconstruct full shower ancestry. Geant4's nuclear category includes hadronic
processes beyond inelastic scattering. Parent momentum is at creation, not at
the collision. `odd/plot-neutral.py --results DIR` uses the five ancestry JSONs
(geant4, charged-only, fatras, 0mev, 50mev) to plot species and acceptance checks.

`odd/verify-replay.py` checks that hit files and every pre-existing truth column
are identical when replaying with the additional parent columns. This verifies
the charged-only control and the ancestry-enabled Geant4 reference separately.

## Scope

This is a baseline, not a production calibration: Si final states are reused for
all materials with local thickness/L0 scaling. No material-dependent tune, elastic
neutron scattering, capture, at-rest transport, antineutron channel, charged-kaon
channel, or native K-long decay is supplied. Results and measured limitations are
recorded in `results/2026-10-14/`, with the existing charged reference unchanged.
