# Strip-only GBTS study, 26 November 2026

Note: `~/notes/atlas/tsi/notebook/2026-11-26_gbts-strip-seeding.md` and `.html`.
Companion folder contains the patches, reports, frozen configurations, summaries and plots. These scripts are local, not yet pushed.

The Athena worktree is `/home/astefl/source/acts/acts-athena-ci/athena-strip-seeding`, branch `study-strip-seeding`; the build uses nightly `2026-11-16T2100` and its unchanged ACTS 48.5.0 library. See the companion manifest for the exact base commit and input paths. `run.sh` sources that build in a fresh shell; always run it in a new working directory.

Reproduce the final comparison (from an empty run directory):

```bash
bash ~/scripts/acts/strip-seeding-20261126/run.sh --events 100 \
  --input /home/astefl/source/acts/acts-athena-ci/run/gbts-seed-split/input/RDO.39626672._000004.pool.root.1 \
  --variants ~/scripts/acts/strip-seeding-20261126/frozen.json \
  --refiners ~/scripts/acts/strip-seeding-20261126/frozen-refiners.json
python ~/scripts/acts/strip-seeding-20261126/summarize.py seeds.jsonl --output summary.json
source ~/scripts/acts/strip-seeding-20261126/env.sh
python ~/scripts/acts/strip-seeding-20261126/compare.py summary.json --log run.log \
  --refiners ~/scripts/acts/strip-seeding-20261126/frozen-refiners.json \
  --names gbts,grid,legacy,tuned,chi4,fit3,fit5 --plots
```

`audit.json` plus `--dump-spacepoints` produces graph/measurement data. `audit_graph.py RUN_DIRECTORY` classifies legacy-only losses. `StripSeedFitStudy` is built from the diagnostic C++ patch; `fit_scan.py` scans its fitted candidates offline. `filter-scan.json` contains the independent gate scan. `refinement-scan.json` / `refiners.json` describe the exploratory refinement run; `validation-candidates.json` / `validation-refiners.json` the corrected training run; `frozen*.json` the final holdout.

`first-pass/` preserves the initial study's scripts/configurations and build recipe. Earlier fit dumps with raw angular covariance or sensor-centre coordinates are superseded by `corrected20`. Use the final source patch and frozen settings for reproduction.

`export_patches.py` separates production changes from the graph dump and fit prototype and checks that the two patches reconstruct the current source tree exactly. `write_note.py` generates the concise MD/HTML note from the final comparison. `compare.py` uses 4,000 deterministic paired event-bootstrap samples and reports unmatched multiplicity as well as fractions.

## Inline implementation follow-up

Production now has one tuned configuration in the existing factory. `run.py` preserves old study variants through frozen JSON data and explicit baseline values; named presets are no longer Athena interfaces. Pass `--configured-defaults` to exercise the new native defaults. `check_inline_config.py after <config-before.json>` verifies full configuration equality, pixel/LRT/custom-table preservation, and explicit overrides. Updated patches and checks are in `studies/strip-seeding-inline-20261126` and linked from the note.
