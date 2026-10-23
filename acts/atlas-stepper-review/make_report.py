from pathlib import Path
import json, html, shutil, os, base64, mimetypes
os.environ.setdefault('MPLCONFIGDIR', '/tmp/acts-atlas-report-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = Path.home() / 'cern/notes/acts/notebook/2026-10-12_atlas-stepper-review'
DATA = json.loads((HERE / 'cpu-results.json').read_text())
LABELS = {'atlas_baseline': 'Reviewed scalar Atlas', 'atlas': 'Updated Atlas', 'sympy': 'SympyStepper', 'atlas_helix': 'Atlas: helix shortcut', 'atlas_gradient': 'Atlas: analytic gradient', 'atlas_numerical_gradient': 'Atlas: numerical gradient', 'atlas_straight': 'Atlas: field disabled'}
COLORS = {'atlas_baseline': '#89939b', 'atlas': '#147d92', 'sympy': '#273f78', 'atlas_helix': '#c48526', 'atlas_gradient': '#8051a0', 'atlas_numerical_gradient': '#b56b9c', 'atlas_straight': '#52874b'}
SOURCE = 'https://gitlab.cern.ch/atlas/athena/-/blob/c5982a1efd76fe5528cc550f4dc0a87371ec1c67/Tracking/TrkExtrapolation/'
RK = SOURCE + 'TrkExRungeKuttaPropagator/src/RungeKuttaPropagator.cxx'
JAC = SOURCE + 'TrkExUtils/TrkExUtils/JacobianHelper.h'

def rows(field, covariance, variants):
    return [next(r for r in DATA['summary'] if r['field_tesla'] == field and r['covariance'] == covariance and r['variant'] == v) for v in variants]

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42})
def panel(ax, data, title):
    values = [r['median_ns']/1000 for r in data]
    lo = [(r['median_ns']-r['min_ns'])/1000 for r in data]
    hi = [(r['max_ns']-r['median_ns'])/1000 for r in data]
    ax.barh(range(len(data)), values, color=[COLORS[r['variant']] for r in data], height=.57, xerr=[lo, hi], capsize=3, error_kw={'linewidth': 1})
    ax.set_yticks(range(len(data)), [LABELS[r['variant']] for r in data])
    ax.invert_yaxis(); ax.set_title(title, loc='left', fontweight='bold', pad=12)
    ax.set_xlabel('Time per track [µs] • lower is faster')
    ax.set_xlim(0, max(r['max_ns']/1000 for r in data)*1.22)
    ax.xaxis.grid(True, alpha=.15); ax.set_axisbelow(True)
    for y,v in enumerate(values): ax.text(max(v, data[y]['max_ns']/1000)+ax.get_xlim()[1]*.02, y, f'{v:.3f}', va='center', fontsize=9)

with PdfPages(HERE / 'plots/cpu-comparison.pdf', metadata={'Title': 'Atlas stepper review — CPU comparison', 'Author': 'ACTS development logbook', 'Subject': '2026-10-12, Apple M3 Pro, five repetitions'}) as pdf:
    fig, axes = plt.subplots(2,1, figsize=(10,8.2))
    for cov,ax in zip([False,True],axes): panel(ax,rows(2,cov,['atlas_baseline','atlas','sympy']),f'2 T, covariance {"on" if cov else "off"}')
    fig.suptitle('Atlas stepper: default-path comparison', fontsize=17, x=.06, ha='left')
    fig.text(.06,.055,'Apple M3 Pro · AppleClang 21 · Release -O3 · pT = 1 GeV · path = 5 m\nFive serial repetitions × 50,000 tracks; 2 s warmup per process. Bars: median; whiskers: min–max.\nBaseline = reviewed scalar commit 8e3dcf0921. Synthetic constant-field sample; no production claim.',fontsize=9)
    fig.subplots_adjust(left=.28,right=.96,top=.90,bottom=.19,hspace=.58); pdf.savefig(fig); plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(10,9))
    panel(axes[0],rows(2,True,['atlas','atlas_helix','sympy','atlas_gradient','atlas_numerical_gradient']),'2 T, covariance on: optional numerical paths')
    panel(axes[1],rows(0,True,['atlas','atlas_straight','sympy']),'0 T, covariance on: one accepted integration step')
    fig.suptitle('Optional paths: costs and scope', fontsize=17,x=.06,ha='left')
    fig.text(.06,.045,'Same setup as page 1. Gradient modes perform extra derivative work absent from the SymPy comparator.\nHelix threshold = 1 m; constant field within each step. Its error estimate omits field variation.\nThe zero-field sample is dominated by setup. Whiskers are ranges, not confidence intervals.\nRepeated equal timings reflect timer/reporting granularity; they do not establish zero uncertainty.',fontsize=9)
    fig.subplots_adjust(left=.30,right=.96,top=.90,bottom=.19,hspace=.48); pdf.savefig(fig); plt.close(fig)

md = f'''# Atlas stepper review and numerical paths

## 12.10.2026

- **Verdict:** retain AtlasStepper as an explicitly non-production performance reference. Recommend SympyStepper or EigenStepper for production tracking. The ported paths improve coverage; they do not establish a general speed advantage.
- Branch: `atlas-stepper-review`; tested source: `{DATA['tested_source_commit']}`. Worktree clean after the three commits.
- [Interactive report](2026-10-12_atlas-stepper-review.html) · [CPU plots, PDF only](2026-10-12_atlas-stepper-review/plots/cpu-comparison.pdf) · [Raw timings, commands and executable hashes](2026-10-12_atlas-stepper-review/cpu-results.json).

### Stacked packages

| Commit | Package |
| --- | --- |
| `8e3dcf0921` | Correctness fixes, concise shared transformations, introduction and historical provenance. |
| `5c9523331d` | Two-lane angular Jacobian, field-gradient transport, helix shortcut and exact straight-line path. |
| `ae78ad600a` | Compile-time stepping modes, benchmark controls and repeatable Atlas/SymPy comparison runner. |

### Athena origin and currency

- Christian Gumpert imports the ATLAS RungeKuttaPropagator on **21.09.2016**, ACTS commit `947ff25463c926c6d6506486ece236450822d16a`, message `add migrated ATLAS runge kutta stepper`. Original destination: `Core/include/ACTS/Extrapolation/AtlasStepper.hpp`.
- The import records no exact Athena revision. The implementation is independently adapted; it is not a continuously synchronized copy. ACTS adds time transport and its own adaptive error control.
- Compared against the Athena source at `c5982a1efd76fe5528cc550f4dc0a87371ec1c67` (12.05.2025, latest change to the inspected RungeKuttaPropagator source found during this review). The core Nyström arithmetic remains recognizable. The ACTS version lacked numerical paths and the shared SIMD Jacobian arrangement present there.
- RungeKuttaPropagator source: {RK}
- Jacobian helper: {JAC}
- Stable GitLab references are now in the class introduction and helper documentation. The historical source is old; its age alone does not imply that the integration method is obsolete.

### Correctness and conciseness

- Reinitialization clears stale covariance/Jacobian state. Updates and reinitialization invalidate field samples. Public field queries and failed intermediate lookups no longer overwrite the accepted-step field cache.
- Bound updates honor the supplied q/p sign. Neutral q/p remains exactly zero; time transport uses the fixed momentum hypothesis. Neutrals require a momentum hypothesis to define time of flight.
- Path derivatives are prepared before first transport and after reanchoring. Curvilinear covariance projection uses the actual surface frame, including near the beam axis.
- Adaptive stepping respects retry and cutoff limits, rejects non-finite step/error values, and does not count a zero step as successful propagation.
- Shared bound/free Jacobian initialization and covariance projection replace duplicated hand-expanded setup. Dead flags and debug state are removed; the flat parameter/derivative layout and scaled q/p column are documented.
- Keep the public `Acts::AtlasStepper` name and include path. A prominent non-production warning and propagation documentation express the intended use without breaking existing benchmark callers. The new Jacobian implementation helper lives in `Acts::detail`.

### Numerical features ported

| Feature | Interface / behavior | Assessment |
| --- | --- | --- |
| Vectorized angular Jacobian | Eigen row-major 3×2 matrices carry phi/theta together, following Athena's two-lane arrangement. Existing ACTS q/p equations remain scalar. | Worth retaining; avoids an ATLAS CxxUtils dependency. The combined final change gives a modest covariance speedup, not an isolated proof of the helper's benefit. |
| Spatial field derivatives | `Options::useFieldGradient = true`; optional `Config::fieldGradient` returns G(i,j) = dBi/dxj. Otherwise central differences use `fieldGradientStep = 1 mm`. | Useful for covariance fidelity in varying fields. Prefer analytic derivatives when available. Finite differences add six field queries per gradient and need suitable field-map boundaries and stencil scale. |
| Short-step helix shortcut | `Options::helixStep` is an absolute length threshold; zero disables it. Hold the field constant within a step, refresh for the next step. Gradient transport disables this shortcut. | Keep opt-in: the RK error estimate does not account for neglected spatial field variation. Near-SymPy speed in a uniform field does not justify enabling it generally. |
| Exact straight-line stepping | Neutral particles or `Options::useMagneticField = false`; no field queries. Transport position, time and derivatives. | A natural specialized path. Zero-field measurements here are too dominated by setup to establish a general throughput benefit. |

- Compile-time specialization selects Jacobian, gradient and helix modes once per step, keeping optional gradient work out of the default kernel.
- The gradient implementation propagates all spatial Jacobian columns. Failure and non-finite gradient handling precede parameter updates.
- These are adaptations to ACTS field providers, options, units and time propagation, not a verbatim replacement by Athena's propagator.

### Parts still left out

- Athena propagation-to-surface drivers, multiple-surface search and experiment-specific field services. Their responsibilities belong to ACTS Propagator, navigation and field providers; copying them into the stepper would duplicate architecture.
- Volume-material integration and nonlinear free-to-bound corrections. The class introduction documents these limitations. Porting them would be substantial production-oriented work and would undermine the small performance-reference role; use SympyStepper/EigenStepper for production needs.
- Athena's complete driver/error-control conventions and surrounding experiment integration. Retain ACTS interfaces and tests; the new paths do not mean full Athena feature parity.
- Default covariance transport still neglects spatial field derivatives unless explicitly enabled. The polynomial direction normalization, endpoint field reuse and tiny charged-q/p clamp remain intentional historical approximations.

### CPU measurements

- Apple M3 Pro, 6 performance + 6 efficiency cores; macOS 27.0.1 arm64; AppleClang 21.0.0, Eigen 5.0.1; CMake Release `-O3 -DNDEBUG`.
- Synthetic repeated track: pT = 1 GeV, path = 5 m, uniform Bz = 2 T, tolerance = 1e-4, no extra maximum-step restriction. Covariance on/off. Additional zero-field control.
- Five serial repetitions per variant, shuffled order with seed 42; 50,000 measured tracks and two-second warmup per process. No simultaneous build or test jobs during timing. 80 benchmark processes in total.
- Each process reports its benchmark median time per track; below is the median across the five process results. Timing uses the benchmark's steady clock, not hardware cycle counters. These are elapsed CPU-work timings, not OS process CPU-time accounting.
- 2 T samples: 145 accepted integration steps per track. Existing propagator-loop count is 144; the benchmark now prints accepted-step statistics separately. Zero-field samples have one accepted step and zero propagator-loop iterations. The saved baseline lacks the new accepted-step output.

| Mode, 2 T | Covariance off [µs/track] | Covariance on [µs/track] |
| --- | ---: | ---: |
| Reviewed scalar Atlas, `8e3dcf0921` | 5.958 | 7.750 |
| Updated Atlas | 6.125 | 7.375 |
| SympyStepper | 6.125 | 6.875 |
| Atlas helix, threshold 1 m | 6.458 | 6.917 |
| Atlas analytic gradient | — | 20.000 |
| Atlas numerical gradient | — | 23.500 |

- Default updated Atlas takes **4.8% less time with covariance** than the reviewed scalar baseline, and **2.8% more without covariance**. The comparison baseline already includes the first correctness/cleanup package; it is not untouched main.
- SymPy takes **6.8% less time** than default Atlas with covariance and matches its median without covariance. The helix covariance result nearly matches SymPy only in this constant-field sample.
- Analytic-gradient transport costs **2.7×**, numerical gradients **3.2×**, relative to default Atlas with covariance. The analytic callback returns zero for this constant field; both modes exercise extra derivative work absent from the SymPy comparator. Varying-field correctness is tested separately, not benchmarked here.
- Zero-field medians with covariance: Atlas 0.583 µs, explicit straight path 0.542 µs, SymPy 0.500 µs. All three have a 0.375 µs median without covariance. Single-step setup dominates.
- PDF whiskers and HTML ranges show minimum–maximum across five process medians, not confidence intervals. Reported timings are quantized; identical values do not establish zero uncertainty. CPU affinity, frequency and thermal state are not controlled. Results do not establish performance on x86, a realistic field map, detector navigation or material-heavy production workloads.

### Validation

| Suite | Cases passed | Assertions passed |
| --- | ---: | ---: |
| Atlas stepper unit tests | 23 | 585 |
| Atlas constant-field propagation integration | 38,016 | 701,568 |
| Atlas/Eigen constant-field comparison integration | 18,576 | 448,848 |

- Unit regressions cover stale state/field caches, failure recovery, charge changes, neutrals, initial and reanchored derivatives, near-beam frames, retry/cutoff/zero steps, no-field query avoidance, and helix refresh in a varying field.
- Gradient checks compare analytic and central-difference field gradients against finite-difference trajectories through five steps in a fully populated, nonsymmetric, divergence-free linear field. Also check zero-gradient equivalence, lookup failures and invalid finite-difference displacement.
- Both integration binaries run directly; the unit suite also registers with CTest. All final suites pass after specialization. Commit hooks pass. [Unit log](2026-10-12_atlas-stepper-review/unit-tests.log), [Atlas integration log](2026-10-12_atlas-stepper-review/integration-atlas.log), [Atlas/Eigen comparison log](2026-10-12_atlas-stepper-review/integration-comparison.log).

### Reproduce

- Build `ActsUnitTestAtlasStepper`, `ActsIntegrationTestPropagationAtlasConstant`, `ActsIntegrationTestPropagationCompareAtlasEigenConstant`, `ActsBenchmarkAtlasStepper` and `ActsBenchmarkSympyStepper` in Release, with unit tests, integration tests and benchmarks enabled.
- Save the Atlas binary from `8e3dcf0921` before rebuilding at `ae78ad600a`. Pass its path as `--baseline`. Recorded commands, binary SHA-256 hashes, build settings and all 80 outputs are in the archived JSON.

```sh
python3 Tests/Benchmarks/benchmark_atlas_stepper.py /path/to/build \\
  --baseline /path/to/ActsBenchmarkAtlasStepperBaseline \\
  --repeats 5 --toys 50000 --include-zero-field \\
  --output cpu-results.json
```

- Local build used `/tmp/acts-atlas-review-build`, system dependencies from the Spack view, and prebuilt code-generation artifacts copied from a matching local build after checking generating-source hashes. A normal fresh build needs its code-generation dependencies or matching prebuilt artifacts.
- Standalone HTML works offline and embeds the measurements, PDF plots, Markdown note and validation logs; it can be shared as a single file. Exported figures are PDF only. `make_report.py` (`acts/atlas-stepper-review` in https://github.com/andiwand/cern-scripts) regenerates the Markdown, HTML and PDF from the archived JSON with Python and Matplotlib.
'''
(HERE.parent / '2026-10-12_atlas-stepper-review.md').write_text(md)

# Render this report's deliberately small Markdown vocabulary; no external runtime dependencies.
import re

def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    s=re.sub(r'(?<!["\w])(https://[^\s<]+)',r'<a href="\1">\1</a>',s)
    return s.replace('2026-10-12_atlas-stepper-review/', './')

def render_md(md):
    out=[]; inlist=False; intable=False; code=None
    for line in md.splitlines():
        if line.startswith('```'):
            if code is None: code=[]
            else: out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>'); code=None
            continue
        if code is not None: code.append(line); continue
        if not line.startswith('- ') and inlist: out.append('</ul>');inlist=False
        if not line.startswith('|') and intable: out.append('</tbody></table></div>');intable=False
        if line.startswith('#'):
            n=len(line)-len(line.lstrip('#'));out.append(f'<h{n}>{inline(line[n:].strip())}</h{n}>')
        elif line.startswith('- '):
            if not inlist: out.append('<ul>');inlist=True
            out.append('<li>'+inline(line[2:])+'</li>')
        elif line.startswith('|'):
            cells=[x.strip() for x in line.strip('|').split('|')]
            if all(re.fullmatch('[-: ]+',x) for x in cells):continue
            if not intable:
                out.append('<div class="scroll"><table><thead><tr>'+''.join('<th>'+inline(x)+'</th>' for x in cells)+'</tr></thead><tbody>');intable=True
            else:out.append('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in cells)+'</tr>')
        elif line.strip(): out.append('<p>'+inline(line)+'</p>')
    if inlist:out.append('</ul>')
    if intable:out.append('</tbody></table></div>')
    return '\n'.join(out)

page=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atlas stepper · 12 October 2026</title><style>
:root{--ink:#17313e;--muted:#526773;--accent:#147d92;--line:#d6e1e4;--paper:#fff;--bg:#f1f5f5}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:42px 28px 70px}header{border-top:5px solid var(--accent);padding-top:20px;margin-bottom:32px}h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.1;letter-spacing:-.04em;margin:12px 0}h2{font-size:1.55rem}h3{margin-top:32px}a{color:#09677f;overflow-wrap:anywhere}p{max-width:90ch}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.13em;font-weight:700;color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:22px}.card strong{display:block;font-size:2rem;color:var(--accent)}.card span,.muted{color:var(--muted);font-size:14px}.controls{display:flex;flex-wrap:wrap;gap:18px;align-items:end;margin:20px 0}label{display:flex;flex-direction:column;font-size:13px;font-weight:650;gap:6px}select,button{font:inherit;padding:9px 12px;border:1px solid #a4b9c1;border-radius:5px;background:white;color:var(--ink)}button,summary{cursor:pointer}button:hover{background:var(--bg)}select:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #ddb357;outline-offset:3px}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;background:#edf4f5;white-space:nowrap}th,td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.pill{font-size:12px;color:#74521a;background:#fff4da;padding:2px 7px;border-radius:4px;white-space:nowrap}code{font:13px ui-monospace,monospace;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f5f6;border-radius:6px;padding:16px;font-size:12px}details{margin-top:22px;border-top:1px solid var(--line);padding-top:18px}summary{font-weight:650}li{margin:8px 0}footer{font-size:13px;color:var(--muted);margin-top:36px}.report h1{font-size:1.9rem;letter-spacing:-.02em}.report h2{font-size:1rem;color:var(--muted)}@media(max-width:660px){main{padding:24px 14px}.cards{grid-template-columns:1fr}.card{padding:14px}.panel{padding:14px}}@media print{body{background:white}main{max-width:none}.controls,button{display:none}details{display:block}}
</style></head><body><main><header><div class="eyebrow">ACTS development logbook · 12 October 2026</div><h1>Atlas stepper review</h1><p>Historical provenance, correctness fixes, numerical paths and a repeated comparison with SympyStepper. Atlas remains a non-production performance reference.</p><a href="../2026-10-12_atlas-stepper-review.md">Markdown note</a> · <a href="plots/cpu-comparison.pdf">CPU plots · PDF</a> · <a href="cpu-results.json" download>Raw results · JSON</a><div class="cards"><div class="card"><strong>−4.8%</strong><span>Atlas time with covariance vs reviewed scalar baseline</span></div><div class="card"><strong>+2.8%</strong><span>Atlas time without covariance vs reviewed scalar baseline</span></div><div class="card"><strong>56,615</strong><span>Unit and integration cases pass</span></div></div></header>
<section class="panel" aria-labelledby="explorer-title"><div class="eyebrow">Interactive measurements</div><h2 id="explorer-title">Compare benchmark modes</h2><p class="muted">Apple M3 Pro · Release −O3 · pT 1 GeV · path 5 m · five serial repetitions × 50,000 tracks. Times below are medians of process benchmark medians; ranges are min–max, not confidence intervals.</p><div class="controls"><label>Magnetic field<select id="field"><option value="2">Uniform 2 T</option><option value="0">Zero field</option></select></label><label>Covariance<select id="cov"><option value="true">On</option><option value="false">Off</option></select></label><label>Relative timing basis<select id="basis"><option value="atlas">Updated Atlas</option><option value="sympy">SympyStepper</option></select></label><label>Mode selection<select id="modes"><option value="all">All measured modes</option><option value="default">Default paths only</option></select></label><button id="reset" type="button">Reset</button></div><p id="context" aria-live="polite"></p><div class="scroll"><table><thead><tr><th>Mode</th><th>Median [µs]</th><th>Range [µs]</th><th>Relative time</th><th>Scope</th></tr></thead><tbody id="results"></tbody></table></div><p class="muted">Lower is faster. Gradient modes include extra derivative work. The helix shortcut neglects within-step field variation; this sample has a constant field. Figures are available only in the linked PDF.</p><details><summary>Individual repetitions and exact commands</summary><div id="trials"></div></details></section>
<details open class="report"><summary>Full findings, implementation and reproduction</summary>__REPORT__</details><footer>Branch <code>atlas-stepper-review</code> · tested source <code>ae78ad600a</code>. Self-contained offline report; no external scripts or services.</footer></main><script id="data" type="application/json">__DATA__</script><script>
'use strict';
const data = JSON.parse(document.getElementById('data').textContent);
const labels = __LABELS__;
const scopes = {atlas_baseline:'After correctness review',atlas:'Default transport',sympy:'Production recommendation',atlas_helix:'Constant-field approximation',atlas_gradient:'Extra derivative work',atlas_numerical_gradient:'Extra derivative work',atlas_straight:'Field queries disabled'};
const order = ['atlas_baseline','atlas','sympy','atlas_helix','atlas_gradient','atlas_numerical_gradient','atlas_straight'];
const ids = ['field','cov','basis','modes'];
const el = id => document.getElementById(id);
function cell(row,value,cls=''){const c=document.createElement('td');c.textContent=value;c.className=cls;row.append(c);}
function render(){
 const field=Number(el('field').value),cov=el('cov').value==='true',basis=el('basis').value;
 const selected=data.summary.filter(r=>r.field_tesla===field&&r.covariance===cov&&(el('modes').value==='all'||['atlas_baseline','atlas','sympy'].includes(r.variant))).sort((a,b)=>order.indexOf(a.variant)-order.indexOf(b.variant));
 const base=data.summary.find(r=>r.field_tesla===field&&r.covariance===cov&&r.variant===basis).median_ns;
 el('results').replaceChildren();el('trials').replaceChildren();
 el('context').textContent=`${selected.length} modes · ${cov?'with':'without'} covariance · ${field===2?'145 accepted steps per track (baseline does not report this count)':'1 accepted step per track; setup dominates'} · relative to ${labels[basis]}.`;
 for(const r of selected){
  const row=document.createElement('tr');cell(row,labels[r.variant]);cell(row,(r.median_ns/1000).toFixed(3),'num');cell(row,`${(r.min_ns/1000).toFixed(3)}–${(r.max_ns/1000).toFixed(3)}`,'num');cell(row,`${(r.median_ns/base).toFixed(3)}×`,'num');cell(row,scopes[r.variant]);el('results').append(row);
  const block=document.createElement('details'),title=document.createElement('summary');title.textContent=labels[r.variant];block.append(title);
  for(const sample of data.samples.filter(s=>s.field_tesla===field&&s.covariance===cov&&s.variant===r.variant).sort((a,b)=>a.repeat-b.repeat)){
   const p=document.createElement('p');p.textContent=`Repetition ${sample.repeat+1}: ${(sample.ns_per_track/1000).toFixed(3)} µs per track`;const pre=document.createElement('pre');pre.textContent=sample.command.join(' ')+'\n\n'+sample.output;block.append(p,pre);
  }el('trials').append(block);
 }
}
ids.forEach(id=>el(id).addEventListener('change',render));el('reset').addEventListener('click',()=>{el('field').value='2';el('cov').value='true';el('basis').value='atlas';el('modes').value='all';render();});render();
</script></body></html>'''
page=page.replace('__REPORT__',render_md(md)).replace('__DATA__',json.dumps(DATA).replace('<','\\u003c')).replace('__LABELS__',json.dumps(LABELS))
# Embed local attachments so the top-level HTML can be shared on its own.
def embed_attachment(match):
    href = html.unescape(match.group(1))
    if href.startswith(('https:', '#')):
        return match.group(0)
    if href == '2026-10-12_atlas-stepper-review.html':
        return '<a href="#explorer-title">'
    attachment = HERE / href
    payload = base64.b64encode(attachment.read_bytes()).decode('ascii')
    mime = mimetypes.guess_type(attachment.name)[0] or 'application/octet-stream'
    return f'<a href="data:{mime};base64,{payload}" download="{attachment.name}">'
page = re.sub(r'<a href="([^"]+)"(?: download)?>', embed_attachment, page)
(HERE.parent / '2026-10-12_atlas-stepper-review.html').write_text(page)
print('Generated Markdown, offline HTML and two-page PDF')
