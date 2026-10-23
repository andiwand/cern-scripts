# Antiproton and antineutron interactions

14 October 2026. In-flight inelastic interactions, including annihilation, use
the existing Fatras correlated-event sampler. Each antiparticle has its own
calibration. No new runtime model, dependency, or tuning parameter is added.
Antiprotons use charged p/pT cuts; enabled antineutrons use the existing neutral
kinetic-energy/time cuts. Stopping and annihilation at rest remain outside scope.

## Reproduce

Reuse the shared external generator and ODD diagnostics:

```
cmake -S ../fatras-neutral-hadrons -B /tmp/antinucleon-generator \
  -DGeant4_DIR=/path/to/Geant4/lib/cmake/Geant4
cmake --build /tmp/antinucleon-generator
python3 calibrate.py --build /tmp/antinucleon-generator \
  --data-root /path/to/Geant4/data --output data/2026-10-14
python3 ../fatras-neutral-hadrons/combine.py \
  ../fatras-pion-validation/data/2026-10-14/silicon-pion-extended.table \
  data/2026-10-14/silicon-antinucleons.table \
  --output data/2026-10-14/silicon-all.table
```

`calibrate.py` produces 100 nodes/species from 0.1 GeV/c to approximately 7 TeV/c,
512 events/node, seed 14642. The grid continues the previous study: 48 nodes up
to 20 GeV/c plus 52 above. Independent reference: 99 geometric midpoints/species,
256 events/point, seed 17542. Geant4 11.3.2 FTFP_BERT, silicon. Original channels
are preserved verbatim. As before, the aggregate untransported remnant includes
nuclear fragments and energy deposits.

Build `check.cpp` using `../fatras-neutral-hadrons/build-check.py`, then check
both `silicon-all.table` and `silicon-midpoints.table`. Compare the independent
reference using `../fatras-neutral-hadrons/compare.py` with the training and
midpoint files and `--output data/2026-10-14/midpoint-comparison.json`.

Build the shared diagnostic module with
`../fatras-pion-validation/build-diagnostics.py --acts-build BUILD --output
../fatras-pion-validation/pion_diagnostics.so`. The module name and PionWriter
class retain their historical names for compatibility. Run from this directory:

```
bash ../fatras-neutral-hadrons/odd/run-env.sh ../fatras-pion-validation/run.py fatras \
  --input /path/to/identical-inputs --output /tmp/odd-antinucleons --events 20 \
  --table data/2026-10-14/silicon-all.table --reference-material \
  --material-map ../fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root \
  --projectiles -2212 -2112 --diagnostic-prefix antinucleon
```

For the baseline, supply the previous pion-extended table with the same corrected
map. For Geant4 diagnostics use mode `geant4`. The supplied table only defines
reference hazard in diagnostic records; it does not change Geant4 physics.
The wrapper and module build helper contain workstation paths; adapt these when
moving installations. Python analysis needs numpy, pandas, matplotlib and uproot.

`analyse.py --truth DIR --output JSON [--diagnostics G4_DIR]` counts common-cut
pixel hits by immediate nuclear-parent species. Geant4 diagnostics add explicit
in-flight, at-rest, fragment, elastic, cutoff and unmatched categories. Reuse
old Geant4 truth only after checking every hit CSV matches, including barcodes.
No matching interaction record means an explicit unmatched vertex. Parent mass
constants in the analysis are the pinned Geant4 proton/neutron masses.

`../fatras-pion-validation/compare.py` delegates to the shared 11-page ODD plotter.
Supply `--geant4`, `--baseline`, `--fatras`, `--output`, labels, and the explicit
revision/map overrides when comparing the old reference geometry metadata to
the corrected Fatras map. Input and other geometry checks remain active.

`plot.py --results DIR --calibration midpoint-comparison.json` reads
`geant4-ancestry.json`, `baseline-ancestry.json`, and `fatras-ancestry.json` in DIR.
It writes `antinucleon_diagnostics.pdf`, separate PDFs/PNGs and the numerical
summary. All plots can be regenerated from the archived JSON/NPZ data.

## Measured result and cost

20 identical ttbar + PU200 events, seed 42, ODD pixels, Bz=2 T; hit-entry
p>=100 MeV, pT>=50 MeV. Secondary hits rise from 13244.10 to 13968.95/event:
+724.85 +/-82.52 (paired event SEM), +5.47%. Coverage rises from 72.79% to 76.77%
of Geant4 (18195.55). Primary hits change from 46434.85 to 46350.30, compared
with Geant4 47191.40. No rate/multiplicity fit.

Fatras directly produces 626.30 antinucleon-origin hits/event. Geant4 has 776.85:
661.80 within model cuts, 54.65 at rest, 55.05 fragments, and 5.35 other/cutoff/
unmatched contributions. This immediate-parent accounting is not a net cascade
gain prediction. Geant4 pre-step momentum does not resolve continuous energy
loss in the interaction-ending step. Surface material and a silicon reference
are still approximations to the actual material. Eight G4 hits across 20 events
lack a matched interaction vertex; no ambiguous vertices occur.

Review fixes preserve parent links through conversion, bremsstrahlung and Geant4
decays; they do not change hits or kinematics. All 20 baseline events and Geant4
hit files replay identically. Pion attribution now retains missing records as
unmatched and handles an empty interaction table; all old 20-event results are
unchanged. The duplicated 800-line ODD plotter is removed.

Conservation: 557056 combined and 101376 midpoint runtime samples pass; maximum
relative four-momentum residual is 1.58e-13. Zero generator null collisions.
Largest midpoint rate discrepancy is 0.0502%; mean charged-multiplicity shifts
are -0.099 (antiproton) and -0.151 (antineutron), with larger point fluctuations.
These checks do not validate every angular or material-dependent distribution.
264 Fatras integration cases and focused physics/selector/ancestry tests pass.
All 20 events finish with no failed Fatras tracks (baseline: three charged
maximum-step failures). Geant4 retains 14 hit-buffer warnings; this does not
establish that charged navigation failures are fixed in general.

Cost is predominantly calibration storage/loading: combined text grows from
226 to 400 MiB; single load measurements 3.13 to 5.55 s, max RSS 191.1 to 335.8
MiB. Tables are immutable/shared; loading is paid once per job. Sequencer times
including diagnostics and CSV I/O are 21.39 and 21.82 s, not a controlled speed
benchmark. Runtime physics uses the same lookup and sampler as existing species.

Inputs/results live in `data/2026-10-14/` and `results/2026-10-14/`, ignored by git.
The next wholly missing projectile family in this reference is charged kaons
(509.55 direct hits/event); that reference count is not a predicted net gain.
