#!/usr/bin/env python3
"""Archive compact evidence after the runtime-sized candidate's full validation."""
import json,shutil,subprocess
from pathlib import Path
root=Path('/home/astefl/source/acts/acts-athena-ci')
run=root/'run/native-pixel-nn/generic'
out=Path('/home/astefl/notes/atlas/tsi/notebook/2026-11-24_native-pixel-nn-final-candidate/mr-review/generic')
full=run/'full';dest=out/'full';dest.mkdir(parents=True,exist_ok=True)
assert 'FULL VALIDATION COMPLETE' in (full/'pipeline.log').read_text()
assert '100% tests passed' in (full/'tests-final-off.log').read_text()
restored=json.loads((full/'restore-equivalence.json').read_text())
assert restored['native_file_hash_restored'] and restored['loaded_code_data_identical_except_build_id']
for source,target in {
 'summary.json':'integration.json', 'job-checks.json':'job-checks.json',
 'physics/record-comparison.json':'record-comparison.json',
 'standalone/validation.json':'validation.json','standalone/timing.json':'timing.json',
 'tests-final-on.log':'tests-on.log','tests-final-off.log':'tests-off.log',
 'restore-equivalence.json':'restore-equivalence.json','source-commit.txt':'source-commit.txt',
 'fallback-fixture-correction.md':'fallback-fixture-correction.md',
}.items():
 shutil.copyfile(full/source,dest/target)
subprocess.run(['python3',str(Path(__file__).with_name('count_loc.py')),str(out/'loc.json')],check=True)
review=json.loads((out/'review.json').read_text())
review.update(timing='Actual Athena GCC library: three alternating native-auto/SSE/ONNX cycles, 50k inputs x3, core16; see full/timing.json. Earlier fixed/runtime-sized comparison is retained in summary.json.',onnx_timing='Current cached-name/shape, caller-output adapter measured alongside native in the final actual-library comparison.',fixture_setup='First fallback fixture used absolute paths, which PathResolver logs as errors. Corrected to relative CALIBPATH names and rerun; production code/libraries unchanged.',source_commit=(full/'source-commit.txt').read_text().strip(),
 tests='4/4 unit/configuration tests pass with AVX2 ON and OFF; restored ON code/data match the measured build; the ACTS whole-file hash differs only in nonfunctional metadata after whitespace cleanup.',
 numerics='Actual Athena library: 100k captured inputs x all four heads, auto/SSE versus ONNX, no tolerance violations or multiplicity-choice changes. Cross-compiler 10k-input evidence is retained.',
 integration='Fresh Native and ONNX 100-event ttbar runs, three serial 20-event timing pairs, pre/default-threshold and logged automatic-fallback smoke jobs; all current-build jobs succeed.',
 limitations='No non-AVX hardware available. Startup probes and finite-sample agreement do not prove graph or universal decision equivalence.',
 loc='760 net lines: 164 conversion/validation, 236 inference/types/dispatch, 128 glue including ONNX adapter, 232 tests including fixture generator. Binary fixtures total 97223 bytes excluded. No generated inference code.')
(out/'review.json').write_text(json.dumps(review,indent=2)+'\n')
print(dest)
