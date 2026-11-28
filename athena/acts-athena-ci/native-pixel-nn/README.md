# Native pixel NN

Native (non-ONNX) inference for the ITk pixel clustering NN in Athena: build,
reconstruction A/B against ONNX Runtime, standalone numerical/timing checks.

- Source: `$ACI_BASE/athena-native-pixel-nn` (branch `acts-native-pixel-nn`),
  build: `$ACI_BASE/athena-build-native-pixel-nn`, results: `$ACI_BASE/run/native-pixel-nn`
  (`ACI_BASE=/home/astefl/source/acts/acts-athena-ci`).
- Standalone tools reuse `../nn-inference` (`env.sh`, captured inputs
  `$NN_STUDY_ROOT/captured-inputs.bin`); they are not production dependencies.
- Run everything sequentially: never rebuild a library or edit a running script
  while reconstruction or timing runs.

## Build and reconstruction

| script | usage |
|---|---|
| `env.sh` | nightly 2026-11-23 environment (sourced by the others) |
| `build.sh [CMAKE_ARGS]` | three-package overlay (`package_filter.txt`), AVX2 dispatch ON; `-DSICLUSTERIZATION_NATIVE_NN_AVX2=OFF` omits the AVX2 kernel |
| `tests.sh` | native NN, inference config and ACTS reconstruction ctests into the build's `tests.log` |
| `run.sh OUT Native\|OnnxRuntime\|Default EVENTS RDO [THREADS=0]` | one Reco_tf job via `config.py`; refuses an existing `OUT/reco.log` |
| `extract.sh DIR EVENTS` | per-event/truth/track outcomes into `DIR/outcomes.txt.gz` |
| `summarize.py [ROOT] [--timing-events 20]` | physics counts, gained/lost truth, counter equality, control-normalized timing → `ROOT/summary.json` |
| `compare_records.py [BACKEND=Native] [ROOT]` | discrete track records vs fitted-parameter differences against ONNX |

`config.py` env: `NATIVE_NN_STAGE=post|pre` (calibrate after/before measurement
selection), `NATIVE_NN_THRESHOLD` (min. cluster charge, default 0), `NATIVE_NN_MODEL_DIR`
(replace the models, e.g. for the fallback smoke job).

## Full campaign

```bash
bash build.sh && bash tests.sh
bash campaign.sh $ACI_BASE/run/native-pixel-nn/<tag> > <tag>.log 2>&1
```

`campaign.sh OUT [--input RDO] [--events 100] [--threads 4] [--timing-events 20]
[--cycles 3] [--cpu 16] [--no-standalone] [--no-fallback] [--no-off-restore]`:
`prepare.py` (fresh OUT, clean source, fallback models) → standalone bench against
the Athena library (validation + timing) → Native/ONNX physics → alternating serial
timing pairs on `--cpu` → pre/default-threshold smoke → incompatible-model fallback
smoke → `analyze.py` (provenance, hashes, counters → `job-checks.json`) →
`check_off_restore.sh` (OFF build + tests, restore ON, loaded ELF sections unchanged).

## Standalone bench

`bench.cxx` loads the four models through the common interface:
`bench dump INPUTS N OUT.bin [MODEL_DIR]` writes all heads (33 floats/input);
`bench time INPUTS N unused` prints `{"us":...}` per number + selected position
inference. Env: `NATIVE_NN_FORCE_SSE=1`, `NATIVE_NN_FORCE_ONNX=1`, `NATIVE_NN_REPEATS`.

| script | usage |
|---|---|
| `bench_env.sh [CMD...]` | nn-inference env + Athena setup; source it or prefix a command |
| `bench_build.sh OUT athena\|gcc\|clang... [--src DIR]` | `OUT/<kind>/bench` against the Athena library, or the package sources compiled with GCC/Clang (`--src`: edited copy of `src/` for kernel A/B) |
| `validate_outputs.sh OUTDIR [--count 100000] [--ref onnx] [--identical A=B] [--models DIR] LABEL=BIN[:ENV=V,...]...` | dump each case, check vs the reference (1e-5+1e-4·\|ref\|, no multiplicity change) with `check_outputs.py` → `validation.json` |
| `bench_env.sh python3 bench_time.py --case LABEL=BIN[:ENV=V,...]... --out DIR [--cycles 3] [--inputs 50000] [--repeats 3] [--cpu 16]` | alternating pinned timing, paired change vs the first case → `timing.json` |
| `bench_env.sh python3 isa_audit.py OUT [--objects clang=DIR] [--debug]` | objdump/nm: no AVX outside the AVX2 kernel, no global Eigen symbols in ISA objects; `--debug` checks -O0 and -O1+sanitizer builds |
| `elf_sections.py snapshot\|compare\|extract` | loaded-section hashes, to show a rebuild leaves measured code/data unchanged |
| `mutate_models.py [OUT]`, `validate_layout.sh BENCH MUTATIONS OUT` | changed-model acceptance (weights, metadata, extra tensor) and rejection cases |
| `count_loc.py [OUT.json] [--base COMMIT]` | changed code lines by conversion/inference/glue/tests |

Example kernel A/B (each bench links its own library through its rpath; `R` = a results dir, `base` an earlier `bench_build.sh` output):

```bash
bash bench_build.sh $R/ab gcc --src /tmp/edited-src
bash validate_outputs.sh $R/ab --identical new=old new=$R/ab/gcc/bench old=$R/base/gcc/bench onnx=$R/ab/gcc/bench:NATIVE_NN_FORCE_ONNX=1
bash bench_env.sh python3 bench_time.py --out $R/ab --cycles 7 --case old=$R/base/gcc/bench --case new=$R/ab/gcc/bench
```

Notes: `atlas/tsi/notebook/2026-11-24_native-pixel-nn*.md` in `andiwand/cern-notes`.
The earlier Eigen candidate, CxxUtils/tuning prototypes, dispatch, roofline and
per-note packaging scripts are in this folder's git history.
