#!/usr/bin/env python3
import hashlib,json,statistics
from pathlib import Path
OUT=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/cxxutils/tuning')
rows=[json.loads(line) for line in (OUT/'final-timing.jsonl').read_text().splitlines()]
timing=json.loads((OUT/'final-summary.json').read_text());comparisons={};validation={}
for compiler in ['gcc','clang']:
 values={(r['label'],r['cycle']):r['us'] for r in rows if r['compiler']==compiler}
 comparisons[compiler]={}
 for isa in ['sse','avx2']:
  for ref in [f'eigen_{isa}',f'common_{isa}','eigen_sse']:
   pct=[100*(values[f'tuned_{isa}',cycle]/values[ref,cycle]-1) for cycle in range(1,7)]
   comparisons[compiler][f'tuned_{isa}_vs_{ref}']={'mean_percent':statistics.mean(pct),'cycle_sd_percent':statistics.stdev(pct)}
 raw=json.loads((OUT/compiler/'validation/validation.json').read_text())
 validation[compiler]={key:{metric:v[metric] for metric in ['finite','max_abs','max_scaled','argmax_changes','elements_outside_1e-5_plus_1e-4_relative','max_relative_precision_error_selected_model']} for key,v in raw['backends'].items()}
result={'date':'2026-11-24','scope':'Standalone compute only; no reconstruction or physics checks. Athena candidate remains fd1750c6d06.',
 'method':'Threadripper 3970X CPU 16; GCC 15.2 / Clang 20.1.8, O2, no fast-math; 100k captured inputs repeated five times per measurement, six alternating cycles. Number plus selected position network. Times exclude loading and cluster preparation.',
 'selection':json.loads((OUT/'selected.json').read_text()),'timing':timing,'paired_comparisons':comparisons,
 'changes':['CxxUtils GEMV with up to eight independent accumulators; no custom exponential.',
            'Eigen exponential on Array<float,4,1> / Array<float,8,1>; CxxUtils blend/divide avoids scalar Eigen Select evaluator.',
            'AVX2 activation unrolled four times; SSE uses normal loop. Small-head sums stay local until final output store.',
            'Bias remains added after accumulation. Bias-first experiment did not consistently improve both compilers.',
            'ISA objects built with hidden visibility, with distinct Eigen array types. No overlapping or exported Eigen helpers.',
            'AVX2 and FMA checked once per model; explicit baseline and optimized kernels.'],
 'validation':validation,'clean_verification':json.loads((OUT/'clean-verification.json').read_text()),
 'loc':json.loads((OUT/'loc.json').read_text()),
 'limits':['Numerical agreement and symbol/instruction audits are not physics validation.',
           'Forced SSE tested on an AVX2 host; no non-AVX hardware/emulator available.',
           'Prototype has not been integrated into Athena build/configuration or production tests.'],
 'remaining_potential':'Input preparation inside inference, softmax and cache/register tuning may offer smaller gains. Not measured here. Keep Eigen exp; no custom transcendental approximation.',
 'roofline':'Earlier empirical dense-only AVX2 lower bound is about 1.14 us for number+pos1. It excludes activation/output transforms and is not an attainable full-inference target.'}
(OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(comparisons,indent=2))
