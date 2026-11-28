#!/usr/bin/env python3
"""Write identical concise MD and HTML reports from the frozen validation."""
from pathlib import Path
import html,json,re,shutil
root=Path('/home/astefl/source/acts/acts-athena-ci')
study=root/'studies/strip-seeding-followup-20261126';run=root/'run/strip-seeding-followup-20261126/holdout100'
notes=Path('/home/astefl/notes/atlas/tsi/notebook');slug='2026-11-26_gbts-strip-seeding';art=notes/slug
result=json.loads((run/'comparison.json').read_text());rows={r['name']:r for r in result['rows']}
ci=next(r for r in result['paired_bootstrap'] if r['name']=='chi4' and r['reference']=='legacy')['efficiency_difference_ci_pp']
blocks=[]
def paragraph(s):blocks.append(('p',s))
def bullets(s):blocks.append(('ul',s))
paragraph(f'2026-11-26. Strip seeding only; no pixel seeding or track finding. RUN4-03, nightly 2026-11-16, unchanged ACTS 48.5.0. Tune on 20 events; validate the frozen settings on **{result["events"]} previously unused events**, {result["denominator"]:,} eligible particles.')
paragraph(f'**The original deficit is confirmed:** GBTS efficiency {100*rows["gbts"]["efficiency"]:.2f}% versus legacy {100*rows["legacy"]["efficiency"]:.2f}%, with {100*rows["gbts"]["unmatched_fraction"]:.2f}% unmatched seeds. The best inexpensive improvement tested is a looser strip filter.')
headers=['Setting','Efficiency %','Pure efficiency %','Unmatched %','Unmatched/event','CPU ms/event']
labels={'gbts':'GBTS default','grid':'Grid triplet','legacy':'Legacy ITk','tuned':'GBTS first tuning','chi4':'GBTS relaxed filter','fit3':'Strip fit, 3σ','fit5':'Strip fit, 5σ'}
table=[]
for name in labels:
 r=rows[name];table.append([labels[name],f'{100*r["efficiency"]:.2f}',f'{100*r["pure_efficiency"]:.2f}',f'{100*r["unmatched_fraction"]:.2f}',f'{r["unmatched_per_event"]:.0f}',f'{r["cpu_ms"]:.0f}'])
blocks.append(('table',(headers,table)))
paragraph('Efficiency: charged stable truth, pT > 1 GeV, |η| < 4, production radius < 300 mm, true space points on ≥3 strip layers. Matched: ≥3 and ≥50% of seed space points share the particle; pure: all do. Unmatched includes seeds without cluster truth. CPU is approximate serial seeding cost; fit rows include candidate production.')
bullets([
 f'**Relax the per-hit filter gates from 5/6 to 20/24.** Efficiency exceeds legacy by {100*(rows["chi4"]["efficiency"]-rows["legacy"]["efficiency"]):.2f} percentage points (paired 95% interval {ci[0]:.2f}–{ci[1]:.2f}). It lowers the unmatched fraction versus default GBTS, but produces more unmatched seeds/event. In the training audit, disabling filter cuts recovers 515 of the 1,007 particles found only by legacy.',
 '**Other retained settings:** phi limit 0.025; barrel–barrel / barrel–endcap / endcap–endcap tau tolerances 0.020/0.025/0.035; strip half-length fraction 1.075; filter |z0| < 150 mm; shared-hit threshold 0.9. The 31-link topology stays unchanged. Adding links mostly adds fakes; tighter strip calibration loses efficiency. Connection-specific tau cuts help after global-cut and topology scans.',
 '**Impact cuts need strip uncertainties.** Existing `d0Max` does not act on strips. Fitting the individual strip measurements and cutting |d0| < 5 mm + Nσ gives the lower-fake alternatives above, at roughly three times the GBTS CPU. The 3σ cut costs endcap efficiency: 83.1% versus 92.0% for relaxed GBTS at 1.5 < |η| < 2. The approximate field/scattering and empirical uncertainties make this a prototype.',
 '**Next decision:** the Athena configuration change is the strongest MR candidate; no ACTS change is needed for this gain. Four tests pass and default counts are unchanged. The 150 mm z0 cut loses efficiency in production-z tails. Track-level validation and a broader sample remain necessary before changing defaults. No MR opened.'
])
paragraph(f'[Plots]({slug}/comparison.png) · [Detailed findings]({slug}/followup-report.md) · [Counts and intervals]({slug}/comparison.json) · [Production patch]({slug}/athena-tuning.patch). Scripts: `acts/strip-seeding-20261126` in https://github.com/andiwand/cern-scripts (local, not pushed).')
paragraph('**Implementation follow-up:**one proposed production configuration, directly in `ActsStripGbtsSeedingToolCfg`; the extra Python module and preset factory are removed. Alternatives above remain study results. The complete configuration matches the validated relaxed point; four tests pass. [Updated patch](2026-11-26_gbts-strip-seeding/athena-inline-tuning.patch) supersedes the preset-based implementation.')
paragraph('Draft MR: https://gitlab.cern.ch/atlas/athena/-/merge_requests/92809 — one primary configuration, required wiring and tests; labelled `AI-assisted`.')
md=['# Strip-only GBTS tuning','']
for kind,x in blocks:
 if kind=='p':md.extend([x,''])
 elif kind=='ul':md.extend(['- '+s for s in x]+[''])
 else:
  h,t=x;md.extend(['| '+' | '.join(h)+' |','|'+'|'.join(['---']+['---:']*(len(h)-1))+'|']+['| '+' | '.join(r)+' |' for r in t]+[''])
(notes/(slug+'.md')).write_text('\n'.join(md))
def inline(s):
 s=html.escape(s)
 s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
 s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
 s=s.replace('https://github.com/andiwand/cern-scripts','<a href="https://github.com/andiwand/cern-scripts">https://github.com/andiwand/cern-scripts</a>')
 return s
style='''
:root{--bg:#f7f7f4;--fg:#15171a;--line:#d9dbd6;--link:#2a78d6;--wash:#eeefea}
@media(prefers-color-scheme:dark){:root{--bg:#131413;--fg:#f2f2ee;--line:#34363a;--link:#5598e7;--wash:#242523;color-scheme:dark}}
body{background:var(--bg);color:var(--fg);font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;font-size:15px;line-height:1.55;margin:0}
main{max-width:880px;margin:auto;padding:32px 16px 64px}h1{font-size:1.65rem;line-height:1.2;font-weight:600}p{margin:16px 0}li{margin:12px 0}ul{padding-left:22px}a{color:var(--link)}code{font-size:.86em;background:var(--wash);padding:1px 4px;border-radius:3px;overflow-wrap:anywhere}.tw{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.86rem;font-variant-numeric:tabular-nums}th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{white-space:normal}a:focus-visible{outline:2px solid var(--link)}
'''
body=['<h1>Strip-only GBTS tuning</h1>']
for kind,x in blocks:
 if kind=='p':body.append('<p>'+inline(x)+'</p>')
 elif kind=='ul':body.append('<ul>'+''.join('<li>'+inline(s)+'</li>' for s in x)+'</ul>')
 else:
  h,t=x;body.append('<div class="tw"><table><thead><tr>'+''.join('<th scope="col">'+html.escape(s)+'</th>' for s in h)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(s)+'</td>' for s in r)+'</tr>' for r in t)+'</tbody></table></div>')
page='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Strip-only GBTS tuning — 26 November 2026</title><style>'+style+'</style></head><body><main>'+''.join(body)+'</main></body></html>\n'
(notes/(slug+'.html')).write_text(page)
print(f'Wrote {slug}.md and .html; {len(" ".join(md).split())} whitespace-separated words including table and links.')
