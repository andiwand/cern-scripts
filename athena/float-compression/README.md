# Float compression study on DAOD_PHYSLITE

Measures what mantissa truncation and byte shuffling do to the compressed
size of the float32 columns of an ATLAS xAOD file. The truncation replicates
`CxxUtils::FloatCompressor` (round to nearest, then mask). The shuffle is the
RNTuple split encoding (all first bytes, then all second bytes, ...).

Note: `atlas/tsi/notebook/2026-10-30_run4-storage-float-compression.md` in
the notes repo.

```bash
python -m venv venv && ./venv/bin/pip install uproot zstandard numpy lz4
curl -L -o physlite.root \
  https://opendata.cern.ch/eos/opendata/atlas/rucio/mc20_13TeV/DAOD_PHYSLITE.38191150._000007.pool.root.1
./venv/bin/python float_compression_study.py physlite.root
```
