# Material locality and missing photon-process diagnostics

Follow-up to `../fatras-secondary-gap/`. The accepted inclusive numerical Fatras
reference is unchanged. This investigation checks the material map, controlled
electron starts and exact Geant4 creator subtypes.

## Measurements

- The current ODD map assigns material to 123 non-sensitive surfaces and none of
  the 18824 sensitive surfaces. Pixel barrel production cylinders lie several
  millimetres outside the actual sensor planes.
- A conservative transverse reachability bound is evaluated for retained
  ionisation births. Longitudinal sensor limits are ignored, so a rejection is
  sufficient to exclude a vacuum helix reaching any pixel sensor before another
  interaction. This is a geometry diagnostic, not an occupancy selection.
- 2400 electron probes compare starts inside a physical sensor with starts on
  its mapped cylinder. Every primary hit is counted. G4 keeps its default physics
  and physical ODD ID boundary. The Fatras control retains the accepted four-turn,
  5 mm numerical settings; a separate control disables all interactions/decays.
- Observational Geant4 callbacks forward every original callback without changing
  tracks or drawing random numbers. They record creator names, birth material,
  photon-parent birth energy and hit-ending steps. Per-event secondary and pixel
  totals reconcile with standard CSV output; all six standard event CSVs match
  the archived reference byte-for-byte. Run IDs distinguish ACTS events, which
  each call G4 BeamOn(1). Birth material is read on the first step, after G4 has
  established the material/cuts couple.

The hit-ending diagnostic mirrors the existing charged sensitive-volume writer.
It is not a replacement hit writer. New debug CPU timings include observational
I/O and must not replace the established reference timings.

## Reproduction

Use a fresh `WORK` directory. NumPy is needed for probes/geometry; Matplotlib for
plots. G4/ACTS scripts run in the established frozen validation environment.

```sh
python build-observer.py --output WORK
~/cern/scripts/acts/fatras-neutral-hadrons/odd/run-env.sh \
  dump-geometry.py --work WORK
python make-probes.py --work WORK
python birth-geometry.py --work WORK
```

Run `run-observer.py --observer-module WORK` through the same environment script,
passing the usual `fatras-runtime-model/run.py` arguments:

- `--mode geant4 --source ~/cern/source/acts/acts/fatras-soft`
- `--revision d419e58b19705e27081e9c718f7c9ead9ddf6f98`
- `--build ~/cern/build/acts/acts/dev3 --threads 1`
- `--material-map ~/cern/scripts/acts/fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root`
- Inclusive: `--input ~/cern/scripts/acts/fatras-runtime-model/results/2026-10-15/inputs --events 3 --output WORK/geant4-observed`
- Probes: `--input WORK/probe-input --events 1 --output WORK/probe-geant4-observed`

For the Fatras probes use `../fatras-transport-performance/run.py`, supplying the
same source and `--module /private/tmp/fatras-transport-work/pruned-build`,
`--input WORK/probe-input --events 1`. Outputs are `WORK/probe-fatras` and
`WORK/probe-vacuum`; add `--transport-only` for the latter. The cached/pruned
bridge is built using that package's documented commands. Mark the full-physics
probe metadata as a deterministic sample (`pileup: null`); the common runner's
generic PU200 label does not describe these inputs.

```sh
python analyse-observer.py --work WORK
python analyse-probes.py --work WORK
python plot.py --work WORK --output WORK/priorities.pdf --preview
python archive.py --work WORK --output results/YYYY-MM-DD
```

Archived probe CSVs and observer TSVs are compressed; analysis readers accept
both forms. The inclusive G4 standard CSVs are already stored in the earlier
reference archive and are not duplicated: independently measured observed hashes
are retained and checked against that archive. The geometry writer produces JSON
under a historical `.csv` filename; `dump-geometry.py` renames it to
`surfaces.json`. Material descriptions retain type/position, not enormous bin
printouts. All these files are optional validation outputs, not physics inputs.

No ACTS defaults or production source are changed. A sensor-local material pilot
must remove the corresponding silicon from the coarse map before an inclusive
comparison, and must handle birth/stopping deposits. Moving all secondaries onto
sensors or adding silicon without subtracting its mapped contribution would not
be a valid physics correction.
