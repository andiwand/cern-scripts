#!/usr/bin/env python3
"""Update today's study note from completed measurements; never invent pending rows."""
import json,shutil,statistics
from pathlib import Path

R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
N=Path.home()/'notes/atlas/tsi/notebook/2026-11-24_nn-inference-latency.md'
A=N.with_suffix('');A.mkdir(exist_ok=True)
d=json.loads((R/'summary.json').read_text())
kernel=json.loads((R/'kernel-summary.json').read_text())
isa=json.loads((R/'vectorization/summary.json').read_text())
paired=json.loads((R/'blocked/paired-summary.json').read_text())
uncal_path=R/'uncalibrated-reference/summary.json'
uncal=json.loads(uncal_path.read_text()) if uncal_path.exists() else None
fraction=json.loads((R/'calibration-fraction.json').read_text())
loc=json.loads((R/'loc-counts.json').read_text())['backends']
labels={'original':'Current ONNX','ort_cached':'Cached ONNX','ort_simple':'Simplified ONNX','direct':'Direct C++ (SSE)','direct_blocked':'Direct C++ (blocked SSE)','direct_avx2':'Direct C++ (AVX2)','sofie':'SOFIE (GEMM)','sofie_gemv':'SOFIE (GEMV)','lwtnn':'LWTNN float','lwtnn_double':'LWTNN double'}
done=len(d['integrated'])==len(labels) and all(len(x['runs'])==3 for x in d['integrated'].values()) and len(d['physics'].get('physics',{}))==len(labels)
prefix=A.name
def fmt(x):return f"{x['mean_us']:.2f} ± {x['sd_us']:.2f}" if x.get('sd_us') is not None else f"{x['mean_us']:.2f}"
def change(b,field):
    if b=='original':return '—'
    x=d['integrated'].get(b,{}).get('comparisons',{}).get(field)
    if not x:return 'pending'
    value=100*(x['normalized_ratio']-1)
    result=f"{value:+.1f} ± {100*x['sd_ratio']:.1f}" if x['sd_ratio'] is not None else f'{value:+.1f} (1 cycle)'
    if 1<len(x['cycle_ratios'])<3:result+=f" ({len(x['cycle_ratios'])} cycles)"
    return result

status='Completed benchmark; see validation limits.' if done and uncal and uncal['complete_pairs']==3 else 'Backend benchmark complete; matched uncalibrated reference in progress.' if done else 'Isolated and 100-event physics comparisons complete; repeated reconstruction timings in progress.'
text=['# Pixel NN inference latency','',f"2026-11-24. {status}",'',
      '**Result:** both networks take '+fmt(d['isolated']['direct_blocked']['0'])+' μs with register-blocked SSE, '+fmt(d['isolated']['direct_avx2']['0'])+' μs with AVX2, and '+fmt(d['isolated']['original']['0'])+' μs through the current ONNX wrapper. Portable SSE dense kernels are already competitive. Runtime overhead and matrix-kernel choice both matter.','',
      '| Backend | Two networks [μs] | After cache sweep [μs] | CKF CPU Δ [%] | Event CPU Δ [%] | LOC: hand / gen |',
      '| --- | ---: | ---: | ---: | ---: | ---: |']
if done:
    gains=d['integrated']['direct_blocked']['comparisons']
    text[4]+=f" In Athena, blocked SSE reduces primary CKF CPU by {100*(1-gains['ckf_ms']['normalized_ratio']):.1f}% and event CPU by {100*(1-gains['event_ms']['normalized_ratio']):.1f}% on this sample."
for b,label in labels.items():
    x=d['isolated'].get(b)
    code=f"{loc[b]['handwritten_loc']} / {loc[b]['generated_loc']}"
    if not x:
        text.append(f'| {label} | pending | pending | pending | pending | {code} |')
        continue
    text.append(f"| {label} | {fmt(x['0'])} | {fmt(x['1048576'])} | {change(b,'ckf_ms')} | {change(b,'event_ms')} | {code} |")
text+=['',
       'μs values cover **multiplicity plus the selected position network**, excluding cluster preparation. ± is cycle-to-cycle SD, not a confidence interval. CKF/event changes are against current ONNX, normalized to unchanged pixel clusterization. The synthetic 1 MiB cache sweep is excluded from timing; its per-call timer overhead is included. Blocked SSE was added later, with a separate paired comparison below.','',
       'LOC = handwritten / generated nonblank, noncomment physical lines across all four models. Handwritten totals include local loading, inference, transforms, kernels and model conversion/generation; shared inference helpers count once per backend. Common harness, includes/imports, build/tests, weights and upstream library code are excluded. These are attributed prototype counts, not production diffs or formatting-independent complexity measures.', '',
       '<details markdown="1"><summary>LOC breakdown and counting scope</summary>', '',
       '| Backend | C++ LOC | Conversion / generator LOC |',
       '| --- | ---: | ---: |']
for b,label in labels.items():
    text.append(f"| {label} | {loc[b]['cpp_loc']} | {loc[b]['conversion_loc']} |")
text+=['',
       f'SOFIE’s generated total includes the four complete headers; the handwritten count includes the generator repairs and, for GEMV, its specialization. Blocked SSE counts the handwritten kernel in the assembled source snapshot. The original ONNX row counts the benchmark adapter, not all existing Athena code. Source hashes and exact attributed ranges: [LOC audit]({prefix}/loc-counts.json).',
       '</details>', '',
       '**Timing limit:** runs are pinned and alternate sequentially, with load/control statistics retained. Two late backend runs and the initial raw control hit host load 30–40; they are retained but excluded and were repeated at lower load. All six accepted raw/NN runs stayed below load 10. Large gains are clear; close backend rankings still need quiet-host confirmation.','',
       '## Remaining cost versus uncalibrated','',
       'The NN charge/size thresholds are zero; the normal **7σ/10σ CKF gates and SeedOnly policy remain active**. Both networks run on each pixel post-calibration call, including repeat visits on different track candidates. Strips and LRT remain uncalibrated.', '']
if uncal and uncal['complete_pairs']:
    text += [f"Matched raw-cluster versus NN comparison, same build, settings and events. Completed {uncal['complete_pairs']}/3 alternating serial pairs of 20 events, first event excluded. Changes include input preparation, calibration application and any resulting tracking-workload changes.", '',
             '| Configuration | CKF [ms/event] | Event [ms/event] | CKF CPU Δ [%] | Event CPU Δ [%] |',
             '| --- | ---: | ---: | ---: | ---: |']
    for mode,label in [('raw','Uncalibrated'),('post','NN post-calibration, blocked SSE')]:
        means=uncal['means'][mode]
        changes=[]
        for field in ['ckf_ms','event_ms']:
            if mode=='raw':changes.append('—');continue
            c=uncal['comparisons'][field]
            changes.append(f"{100*(c['normalized_ratio']-1):+.1f}"+(f" ± {100*c['sd_ratio']:.1f}" if c['sd_ratio'] is not None else ' (1 pair)'))
        text.append(f"| {label} | {means['ckf_ms']:.1f} | {means['event_ms']:.1f} | {changes[0]} | {changes[1]} |")
    text += ['', 'Absolute times are arithmetic means; percentage changes are paired and normalized to pixel clusterization. Repeated events are not pooled as additional physics statistics.', '']
    text += ['This matched measurement supersedes the earlier 28% AVX2 profile estimate. That estimate subtracted timed calibration from five-event CKF wall time and assumed all other work unchanged; it used a different backend, number of events and first-event treatment from this steady-state blocked-SSE comparison.', '']
    raw_counts=uncal['runs']['raw'][0]['tracking_counters']
    post_counts=uncal['runs']['post'][0]['tracking_counters']
    if all(key in raw_counts and key in post_counts for key in ['Used seeds','CKF tracks']):
        text += [f"Tracking workload: {raw_counts['Used seeds']:,} → {post_counts['Used seeds']:,} used seeds; {raw_counts['CKF tracks']:,} → {post_counts['CKF tracks']:,} returned CKF tracks (same 20 events). These totals do not measure internal candidate visits. [Reference data]({prefix}/uncalibrated-reference.json).", '']
else:
    text += ['Matched uncalibrated timing awaits a lower-load window. The first overloaded comparison is not accepted as a measurement of the residual overhead. The earlier forced-seed/LRT study has a different configuration and is not used as the denominator.', '']
    x=fraction['direct_avx2'];g=fraction['sofie_gemv']
    text += [f"**Profile-based estimate:** in five serial events, AVX2 makes {x['calibrations_per_used_seed']:.2f} calibrations per used seed: about {x['calibration_wall_us_per_used_seed']:.0f} μs out of {x['ckf_wall_us_per_used_seed']:.0f} μs primary CKF wall time ({100*x['calibration_fraction']:.1f}%). Removing that block while assuming unchanged remaining work predicts **{100*x['counterfactual_overhead']:.0f}% overhead over uncalibrated**; SOFIE/GEMV gives {100*g['counterfactual_overhead']:.0f}%. These are counterfactual estimates, not measured raw/NN ratios; the denominator is used seeds, including unsuccessful attempts.", '']
text += ['## Physics validation','']
physics=d['physics'].get('physics',{})
same_physics = len(physics)==len(labels) and all(
    all(row[key]==physics['original'][key] for key in ['truth','matched','reco','fakes','duplicate_truth'])
    and row['gained']==row['lost']==0 for row in physics.values())
if same_physics:
    x=physics['original']
    text += [f"All ten backends give **{x['efficiency_pct']:.5f}% efficiency** ({x['matched']:,}/{x['truth']:,} selected truth particles) and **{x['fake_pct']:.5f}% fakes** ({x['fakes']:,}/{x['reco']:,} tracks) on the same 100 ttbar μ=200 events. No backend gains or loses a matched truth particle; duplicate counts and all reported tracking statistics also agree. These four-thread jobs are excluded from timing. Finite-sample agreement does not establish bitwise trajectory equivalence."]
elif physics:
    text+=['Same 100 ttbar μ=200 events per backend; four-thread runs are excluded from timing.','',
           '| Backend | Efficiency [%] | Fake fraction [%] | Matched gained / lost | Fake tracks |',
           '| --- | ---: | ---: | ---: | ---: |']
    for b,label in labels.items():
        if b not in physics:text.append(f'| {label} | pending | pending | pending | pending |');continue
        x=physics[b]
        text.append(f"| {label} | {x['efficiency_pct']:.5f} | {x['fake_pct']:.5f} | {x['gained']} / {x['lost']} | {x['fakes']} |")
    if 'original' in physics:
        x=physics['original'];text+=['',f"Reference: {x['matched']:,}/{x['truth']:,} selected truth particles; {x['fakes']:,}/{x['reco']:,} reconstructed tracks classified as fake. Finite-sample agreement does not establish bitwise trajectory equivalence."]
else:text+=['Full reconstruction results pending.']
profiles=d.get('profiles',{})
if profiles:
    text += ['', '<details markdown="1"><summary>Calibration cost inside Athena</summary>', '',
             'Separate five-event serial diagnostics, including the first event; wall timers are disabled in the performance table. Means below are per NN calibration, including wrappers and input/output work.', '',
             '| Backend | Calls | Prepare [μs] | Number [μs] | Position [μs] | Select/cleanup [μs] | Total [μs] |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for b, x in profiles.items():
        text.append(f"| {labels[b]} | {x['calls']:,} | {x['input_us']:.2f} | {x['number_us']:.2f} | {x['position_us']:.2f} | {x['selection_us']:.2f} | {x['total_us']:.2f} |")
    text += ['', 'Standalone and embedded inference have different cache and allocation histories. Use the measured reconstruction CPU change; do not extrapolate it solely from warm standalone latency.', '</details>']
text+=['',
       'All four network outputs pass `1e-5 + 1e-4 × |reference|` on 100,000 real inputs, with **zero multiplicity changes**. Cached/simplified ONNX are bit-identical there; other implementations differ through floating-point evaluation order. Selected-model precision outputs differ by less than 0.01%. Current ONNX reproduces the preceding SeedOnly study’s 100-event printed outcome records exactly; blocked and original direct SSE also agree exactly with each other.','',
       '## Where OpenBLAS beats direct SSE','',
       'The main gap is the **128 → 64** layer: direct SSE takes 0.81 μs/network, OpenBLAS GEMV 0.61 μs. The direct loop repeatedly loads/stores output sums. Holding 16 outputs in four SSE registers, initialized directly from the biases, reduces this to 0.51 μs while preserving input summation order. Blocking also improves the first layer.','',
       '| Paired whole-network check | Both networks [μs] |',
       '| --- | ---: |']
for b in ['direct','sofie_gemv','direct_blocked']:
    values=paired[b]['0']
    text.append(f'| {labels[b]} | {statistics.mean(values):.2f} ± {statistics.stdev(values):.2f} |')
text += ['',
       'Blocked SSE is 21% faster than the original direct loop and 16% faster than GEMV in this warm comparison. After the cache sweep, blocked SSE and GEMV are approximately equal. All four network outputs remain bit-identical to direct SSE on 100,000 inputs. Register blocking removes OpenBLAS’s warm-latency advantage in this model.', '',
       '<details markdown="1"><summary>Layer breakdown</summary>', '',
       '| Layer | Direct SSE [μs] | OpenBLAS GEMV [μs] | Blocked SSE [μs] |',
       '| --- | ---: | ---: | ---: |']
for row in kernel['rows']:
    text.append(f"| {row['shape']} | {row['sse']:.3f} | {row['gemv']:.3f} | {row['sse_blocked']:.3f} |")
text += ['',
       'Times sum multiplicity + pos1 for each layer, using 512 real inputs, three repeats of 100,000 calls, with loop baseline subtracted. Layers are warmed separately: the sum is not a literal decomposition of whole-network latency. Separate activation probes are similar: 2.05 μs direct versus 1.99 μs generated SOFIE. The GEMV probe uses the original weights in every layer; see the SOFIE serialization detail below.', '',
       f'![Dense-layer comparison]({prefix}/kernel-comparison.png)', '',
       f'[PDF]({prefix}/kernel-comparison.pdf)',
       '</details>', '',
       '<details markdown="1"><summary>Implementation and measurement details</summary>','',
       '- Common setup: Threadripper 3970X, timed jobs pinned to CPU 16; Athena 2026-11-23T2100, repaired pixel NN post-calibration at all charges/sizes, primary only; `SeedOnly`, 7/10σ cuts, ≥3 primary pixel hits. Strips and LRT settings unchanged. No retraining, quantization, GPU work or cut tuning.',
       '- Standalone: 153,721 captured inputs from five events; 30,000 evenly spaced inputs per timing loop, three inner repeats in each of three alternating cycles. The baseline reproduces the current wrapper; integrated runs use the actual Athena path. All four models are validated even when a position network is not selected.',
       '- Integration: three alternating serial 20-event runs/backend, with the first event excluded from steady-state PerfMon CPU. Model loading is outside standalone timing. The prototype retains the original ONNX conditions objects; initialization/memory are not production-optimized. Production integration still needs the normal conditions lifecycle and a portable CPU dispatch policy.',
       '- Compiler: gcc 15.2, `-O2 -DNDEBUG`, no fast-math. Standalone runs preload Athena’s tcmalloc and Intel math libraries. Direct kernels use fixed dimensions and external weights; non-aliasing buffers permit SIMD. Only the AVX2 variant has an explicit CPU target. Scratch storage is per thread.',
       '- Cached ONNX reuses metadata and tensors. Simplified ONNX fixes batch size one and removes tensor manipulation: optimized multiplicity/position graphs shrink from 14/21 to 10/19 nodes. SiLU already fuses in the original runtime graph.',
       '- SOFIE generates from the simplified batch-one ONNX graphs and uses `doInfer` with caller-owned output. ROOT 6.40.02 needs a missing Softmax semicolon repaired; the GEMV specialization also needs its generated output-pointer declaration corrected. Direct C++ and generated SOFIE use a stable sigmoid: the original exponential formula raises overflow for large negative activations despite finite outputs. Output validation also rejects invalid/divide-by-zero/overflow flags. The separate GEMV variant specializes batch-one matrix multiplication. Release OpenBLAS 0.3.33 uses its Nehalem kernel, one thread.',
       '- SOFIE serializes 17 subnormal pos1 parameters as zero (maximum magnitude 6.9×10⁻⁴⁰). They feed only its one-element probability softmax, which is identically one for finite inputs; positions and precisions are unaffected. Every other parameter is bit-identical to the exported float32 weights.',
       '- LWTNN JSON conversion preserves the dense weights; `generic::Stack<float>` and `Stack<double>` share explicit input/output transforms and use LWTNN’s existing sigmoid clipping at ±30. Its scalar Swish promotes the exponential to double even in the float stack. The named-input map interface is bypassed.',
       '- Truth: stable charged generator particles, pT >1 GeV, |η|<4, production radius <300 mm, including pile-up. Evaluate primary `InDetTrackParticles`; efficiency requires match probability >0.5. Fakes have probability <0.5 or nonfinite among tracks with |η|<4; no extra reco pT cut. The 46 tracks at exactly 0.5 are counted separately. Missing truth links alone do not define fakes.',
       '</details>','',
       '<details markdown="1"><summary>Vectorization and portability</summary>','',
       'This Athena build uses `-march=x86-64-v2`: SSE through SSE4.2 is part of the baseline; AVX2/FMA is not. The direct portable backend and generated/Eigen code here use SSE2. Direct AVX2/FMA targets only the dense kernels and needs runtime checks for both CPU features in production. Athena already uses default/AVX2 function multiversioning in `TrkGaussianSumFilterUtils/KLGaussianMixtureReduction.cxx`.', '',
       'SOFIE/GEMV uses the release’s fixed Nehalem OpenBLAS, one thread, with no dynamic architecture dispatch. Its inspected GEMV kernels use 128-bit SSE (`mulps`, `addps`, SSE3 `haddps`), without AVX/FMA. Its latency therefore belongs with the portable SSE comparison. Changing BLAS builds or compiler targets requires a separate measurement.', '',
       'All variants share Athena’s Intel math library and its CPU dispatch. SIMD labels describe the compiled NN code and inspected BLAS kernels; timings are measured on the same AVX2-capable host.', '',
       'Separate alternating comparison of the default SSE2 and Athena-matched compiler targets:', '',
       '| Backend | SSE2 build [μs] | x86-64-v2 build [μs] |',
       '| --- | ---: | ---: |']
for b in ['direct','direct_avx2','sofie_gemv']:
    text.append(f"| {labels[b]} | {fmt(isa['sse2-'+b]['0'])} | {fmt(isa['v2-'+b]['0'])} |")
text += ['',
       'The compiler-target change has little effect (about 1% for direct SSE); all four output arrays remain bit-identical on 100,000 inputs for these three backends. The AVX2 row targets its dense kernels explicitly in both builds.', '',
       'GCC targets: <https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html> · OpenBLAS dispatch: <https://github.com/OpenMathLib/OpenBLAS/blob/develop/USAGE.md>',
       '</details>','',
       '<details markdown="1"><summary>Model cost and the initial estimate</summary>','',
       'Deployed `ITkPixelClusterization/nn-01-01-01`, ONNX opset 17, float32: `67 → 128 → 64 → 32 → 16 → output`, SiLU after the first three layers. The four networks have distinct weights.','',
       '| Network | Weights + biases | Dense FLOPs, batch 1 |','| --- | ---: | ---: |',
       '| number | 19,619 | 38,752 |','| pos1 | 19,653 | 38,816 |','| pos2 | 19,738 | 38,976 |','| pos3 | 19,823 | 39,136 |','',
       'Per calibration: about 78,000 dense FLOPs, 154 KiB of parameters and 448 SiLU activations, plus small input/output transforms. Two FLOPs per multiply-add. The Threadripper 3970X has 512 KiB L2/core and two 256-bit FMA units: about 118 GFLOP/s/core using AVX2/FMA at an assumed 3.7 GHz, giving a 0.66 μs dense-arithmetic lower bound. At assumed effective rates of 10/20/30 GFLOP/s, arithmetic takes 7.8/3.9/2.6 μs. These exclude nonlinear functions and overhead; cache capacity does not establish residency. The initial 5–10 μs complete-calibration target was an estimate; the main table measures inference only.',
       '',
       'The earlier instrumented run measured **34.0 μs/calibration, not 100 μs**: 30.1 μs inside two ONNX calls, 2.8 μs wrappers, 1.1 μs preparation and 0.1 μs selection/cleanup. It included primary + LRT and the first event, with a different seed-forcing setup; do not equate its denominator with the new benchmarks. [Original measurement](2026-11-23_nn-post-calibration/cost-all-charges.json).',
       '</details>','']
for ext in ['png','pdf','svg']:
    source=R/'plots'/f'kernel-comparison.{ext}'
    if source.exists():shutil.copy2(source,A/source.name)
plot=R/'plots/latency-comparison.png'
if plot.exists():
    for ext in ['png','pdf','svg']:shutil.copy2(plot.with_suffix('.'+ext),A/plot.with_suffix('.'+ext).name)
    text+=['<details markdown="1"><summary>Performance plot</summary>','',f'![Inference and reconstruction performance]({prefix}/latency-comparison.png)','',f'[PDF]({prefix}/latency-comparison.pdf)','</details>','']
for filename,source in [('summary.json',R/'summary.json'),('model-manifest.json',R/'model-manifest.json'),('capture-validation.json',R/'capture-validation.json'),('provenance.json',R/'provenance.json'),('sofie-generation-fixes.json',R/'sofie-generation-fixes.json'),('input-summary.json',R/'input-summary.json'),('optimized-graphs.json',R/'optimized-graphs.json'),('kernel-summary.json',R/'kernel-summary.json'),('isa-summary.json',R/'vectorization/summary.json'),('blocked-paired-summary.json',R/'blocked/paired-summary.json'),('outcome-comparisons.json',R/'outcome-comparisons.json'),('artifact-audit.json',R/'artifact-audit.json')]:
    if not source.exists():continue
    shutil.copy2(source,A/filename)
validation=json.loads((R/'validation-real-athena/validation.json').read_text())
shutil.copy2(R/'calibration-fraction.json',A/'calibration-fraction.json')
shutil.copy2(R/'loc-counts.json',A/'loc-counts.json')
shutil.copy2(R/'timing-exclusions.json',A/'timing-exclusions.json')
if uncal_path.exists():shutil.copy2(uncal_path,A/'uncalibrated-reference.json')
shutil.copy2(R/'tracking-counter-comparison.json', A/'tracking-counter-comparison.json')
validation['backends'].update(json.loads((R/'blocked/validation/validation.json').read_text())['backends'])
(A/'numerical-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
weights=json.loads((R/'sofie-weight-validation.json').read_text())
compact={name:{'parameters':row['parameters'],'changed_parameters':sum(len(x['indices']) for x in row['differences']),
               'max_absolute_change':max((abs(a-b) for x in row['differences'] for a,b in zip(x['old_values'],x['new_values'])),default=0)}
         for name,row in weights.items()}
compact['interpretation']='Only pos1 one-element probability softmax parameters differ; all are subnormal values serialized as zero. No model-output effect for finite inputs.'
(A/'sofie-weight-audit.json').write_text(json.dumps(compact,indent=2)+'\n')
text+=['## Suggested next step','',
       'Prefer LWTNN float for production integration: it saves 15.0% event CPU against ONNX, versus 16.1% for blocked SSE. Its roughly 1.3% higher event cost relative to blocked SSE is a small price for using an existing inference implementation instead of maintaining custom kernels. This is an engineering preference; close timing differences need quiet-host confirmation. The measured path uses `generic::Stack<float>` with explicit transforms, bypassing named-input maps.', '',
       'Keep blocked SSE, with external weights, as the performance reference; use it if that remaining gain justifies model-specific maintenance. AVX2 has no resolved full-event advantage here. SOFIE/GEMV is competitive but currently needs generator repairs and batch-one specialization. Production work for the chosen backend still needs conditions integration, thread-safe scratch storage and automated conversion/output checks against ONNX.', '',
       '## Reproduction and references','',
       f'[Counts/timings]({prefix}/summary.json) · [Tracking counters]({prefix}/tracking-counter-comparison.json) · [Numerical validation]({prefix}/numerical-validation.json) · [Model hashes]({prefix}/model-manifest.json) · [Provenance]({prefix}/provenance.json) · [Standalone HTML]({N.with_suffix(".html").name})','',
       'Scripts: `athena/acts-athena-ci/nn-inference` in <https://github.com/andiwand/cern-scripts>. Working data: `~/source/acts/acts-athena-ci/run/nn-inference/`.','',
       'Related fixes: <https://gitlab.cern.ch/atlas/athena/-/merge_requests/92714> and <https://gitlab.cern.ch/atlas/athena/-/merge_requests/92742>','',
       'SOFIE: <https://root.cern.ch/doc/v638/md_tmva_2sofie_2README.html> · LWTNN: <https://github.com/lwtnn/lwtnn> · CPU architecture: <https://docs.archer2.ac.uk/user-guide/hardware/#amd-zen2-microarchitecture>','']
N.write_text('\n'.join(text))
print(N)
