# GBTS seed split in the central barrel

Note: `acts/notebook/2026-11-17_gbts-barrel-seed-split.md` in the notes repo.

Benchmarks from branch `tmp-gbts-barrel-split` of andiwand/acts (main + synthetic
suite + `Tests/Benchmarks/SeedEtaReport.hpp`), built Release in
`~/cern/build/acts/acts/gbts-barrel`.

- `toy.py`: eta = 0 tracks through the ITk pixel barrel radii; fraction of 4/5-SP
  seeds the split check fires on vs pT. `uv run --no-project --with numpy python toy.py`
- `run.sh <tag> [gbts flags]`: GBTS on ITk PU200 seeds 1-20, per-|eta| report.
  `GBTS_HIT_INEFF=0.03` moves 3% of the hits to a random phi on their layer.
- `agg.py <file>`: sums the per-|eta| report over events.

Grid reference: `ActsBenchmarkGridTripletSeeding --layout itk --seed $s --runs 1`.

## Connection table (note `acts/notebook/2026-11-17_gbts-connection-table.md`)

- Athena table: `run.sh athena --connection-table <athena>/Trigger/TrigAlgorithms/TrigFastTrackFinder/share/binTables_ITK_RUN4.txt`
- Hand-written table: `run.sh hand --connection-table none`
- Learn the shipped ITk table (branch default, reproduces `Fatras/data/itk-gbts-connections.txt`):
  `ActsBenchmarkGbtsSeeding --layout itk --train-connection-table out.txt`
  (100 events, seeds 1001+, primaries pT > 0.9 GeV, adjacent + skip-one links, kept if seen >= 1000 times)
