#!/usr/bin/env python3
"""Keep physics event counts separate from repeated timing samples."""
import gzip
import hashlib
import json
import re
import statistics as st
import sys
import tarfile
from pathlib import Path
R=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn')
out={'physics':{},'timing':{}}
records={};truths={}
for backend in ['OnnxRuntime','Native']:
    p=R/'physics'/backend/'outcomes.txt.gz'
    if not p.exists() or not (p.parent/'extract.log').exists():continue
    events={};truth={};rows=[]
    with gzip.open(p,'rt') as stream:
        for line in stream:
            x=line.split();rows.append(line.rstrip())
            if x[0]=='E':events[tuple(map(int,x[1:3]))]=list(map(int,x[3:]))
            elif x[0]=='T':truth[tuple(map(int,x[1:4]))]=(int(x[14])>0,float(x[6]))
    counts=dict(zip(['truth','matched','duplicate_truth','reco','fakes','half'],map(sum,zip(*events.values()))))
    counts.update(events=len(events),efficiency_pct=100*counts['matched']/counts['truth'],fake_pct=100*counts['fakes']/counts['reco'])
    counts['records_sha256']=hashlib.sha256('\n'.join(sorted(rows)).encode()).hexdigest()
    out['physics'][backend]=counts;records[backend]=rows;truths[backend]=truth
if len(truths)==2:
    a,b=truths['OnnxRuntime'],truths['Native'];assert a.keys()==b.keys()
    out['comparison']={'gained':sum(b[k][0] and not a[k][0] for k in a),
                       'lost':sum(a[k][0] and not b[k][0] for k in a),
                       'sorted_records_equal':sorted(records['Native'])==sorted(records['OnnxRuntime'])}
    def counters(backend):
        lines=(R/'physics'/backend/'log.RAWtoALL').read_text().splitlines()
        lines=[re.sub(r'^\d\d:\d\d:\d\d ','',s) for s in lines]
        return [s for s in lines if re.search(r'^\| |Number of truth particles with hits|Space Point Formation statistics|RDO truth stat',s)]
    out['comparison']['tracking_counter_rows']=len(counters('Native'))
    out['comparison']['tracking_counters_equal']=counters('Native')==counters('OnnxRuntime')
for backend in ['OnnxRuntime','Native']:
    rows=[]
    for p in sorted((R/'timing').glob('c*/'+backend)):
        if not (p/'exit-code.txt').exists():continue
        assert (p/'exit-code.txt').read_text().strip()=='0'
        assert 'runArgs.threads = 0' in (p/'runargs.RAWtoALL.py').read_text()
        with tarfile.open(p/'perfmonmt_RAWtoALL.json.tar.gz') as tar:
            data=json.load(tar.extractfile(tar.getmembers()[0]))
        c=data['componentLevel']['Execute'];n=c['ActsTrackFindingAlg']['count'];assert n==19
        rows.append({'cycle':p.parent.name,'events':20,'timed_events':n,
                     'ckf_ms':c['ActsTrackFindingAlg']['cpuTime']/n,
                     'control_ms':c['ActsPixelClusterizationAlg']['cpuTime']/n,
                     'event_ms':data['summary']['snapshotLevel']['Execute']['dCPU']/n,
                     'load_start':(p/'load-start.txt').read_text().strip(),
                     'load_end':(p/'load-end.txt').read_text().strip()})
    out['timing'][backend]=rows
base={x['cycle']:x for x in out['timing']['OnnxRuntime']}
out['normalized']={}
for quantity in ['ckf_ms','event_ms']:
    ratios=[x[quantity]/x['control_ms']/(base[x['cycle']][quantity]/base[x['cycle']]['control_ms']) for x in out['timing']['Native'] if x['cycle'] in base]
    if ratios:out['normalized'][quantity]={'change_pct':100*(st.mean(ratios)-1),'sd_pct':100*st.stdev(ratios) if len(ratios)>1 else None,'ratios':ratios}
(R/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
