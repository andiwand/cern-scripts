#!/usr/bin/env python3
import json,re
from pathlib import Path
root=Path(__file__).resolve().parent
run=root.parent.parent/'run/strip-seeding-20261126/holdout100'
c=json.loads((run/'comparison.json').read_text());s=json.loads((run/'summary.json').read_text())
rows={r['name']:r for r in c['rows']};order=['gbts','grid','legacy','tuned','high_efficiency','purity']
labels={'gbts':'GBTS original','grid':'ACTS grid triplet','legacy':'Legacy ITk','tuned':'GBTS balanced','high_efficiency':'GBTS efficiency','purity':'GBTS purity'}
lines=[f"Independent validation: **{c['events']} events, {c['denominator']:,} eligible truth particles**. The three presets were fixed before this file was read.",'',
'| Configuration | Efficiency [%] | Fully pure-seed efficiency [%] | Fake [%] | Unlinked [%] | Unmatched [%] |',
'|---|---:|---:|---:|---:|---:|']
for n in order:
 r=rows[n];lines.append(f'| {labels[n]} | {100*r["efficiency"]:.2f} | {100*r["pure_efficiency"]:.2f} | {100*r["fake_fraction"]:.2f} | {100*r["unlinked_fraction"]:.2f} | {100*r["unmatched_fraction"]:.2f} |')
lines+=['','| Configuration | Seeds/event | Unmatched/event | Found particles with duplicates [%] | Approx. seed CPU [ms/event] |','|---|---:|---:|---:|---:|']
for n in order:
 r=rows[n];lines.append(f'| {labels[n]} | {r["seeds_per_event"]:.1f} | {r["unmatched_per_event"]:.1f} | {100*r["duplicate_fraction"]:.1f} | {r["cpu_ms"]:.1f} |')
lines+=['','Paired event-bootstrap 95% intervals for the balanced point:']
for p in c['paired_bootstrap']:
 if p['name']!='tuned':continue
 e=p['efficiency_difference_ci_pp'];f=p['unmatched_fraction_difference_ci_pp'];base=rows[p['reference']];r=rows['tuned']
 lines.append(f'Compared with {labels[p["reference"]]}, efficiency changes by {100*(r["efficiency"]-base["efficiency"]):+.2f} percentage points (95% interval {e[0]:+.2f} to {e[1]:+.2f}), and unmatched fraction by {100*(r["unmatched_fraction"]-base["unmatched_fraction"]):+.2f} points ({f[0]:+.2f} to {f[1]:+.2f}).')
lines+=['', 'Efficiency varies across the detector; aggregate gains do not imply improvement in every bin.', '', '| Truth |eta| interval | Eligible particles | Original [%] | Balanced [%] | Efficiency [%] | Purity [%] | Legacy [%] |'.replace('|eta|','absolute eta'), '|---|---:|---:|---:|---:|---:|---:|']
for i,(lo,hi) in enumerate(zip(s['eta_edges'],s['eta_edges'][1:])):
 den=s['totals']['gbts'].get(f'eta{i}_den',0)
 if not den:continue
 vals=[100*s['totals'][n].get(f'eta{i}_num',0)/den for n in ['gbts','tuned','high_efficiency','purity','legacy']]
 lines.append(f'| {lo:g}–{hi:g} | {den:,} | '+' | '.join(f'{x:.2f}' for x in vals)+' |')
lines+=['','The longitudinal cut has an explicit acceptance cost in the production-z tails:', '', '| Truth production |z| [mm] | Eligible particles | Original [%] | Balanced [%] | Legacy [%] |'.replace('|z|','absolute z'), '|---|---:|---:|---:|---:|']
for i,(lo,hi) in enumerate(zip(s['z_edges'],s['z_edges'][1:])):
 den=s['totals']['gbts'].get(f'z{i}_den',0)
 if not den:continue
 label=f'{lo:g}–{hi:g}' if hi<100000 else f'>={lo:g}'
 vals=[100*s['totals'][n].get(f'z{i}_num',0)/den for n in ['gbts','tuned','legacy']]
 lines.append(f'| {label} | {den:,} | '+' | '.join(f'{x:.2f}' for x in vals)+' |')
lines+=['','[Validation plots (PNG)](../../run/strip-seeding-20261126/holdout100/comparison.png) · [PDF](../../run/strip-seeding-20261126/holdout100/comparison.pdf) · [Summary and paired confidence intervals](../../run/strip-seeding-20261126/holdout100/comparison.json). The full binned counts, including pT and production radius, are in `../../run/strip-seeding-20261126/holdout100/summary.json`.']
text='<!-- validation-results -->\n'+'\n'.join(lines)+'\n<!-- end-validation-results -->'
p=root/'README.md';doc=p.read_text()
if '@RESULTS@' in doc:doc=doc.replace('@RESULTS@',text)
else:doc=re.sub(r'<!-- validation-results -->.*?<!-- end-validation-results -->',lambda _:text,doc,flags=re.S)
p.write_text(doc)
