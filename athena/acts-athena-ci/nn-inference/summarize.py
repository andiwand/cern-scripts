#!/usr/bin/env python3
"""Collect completed timing/physics runs without mixing repeated event samples."""
import collections,gzip,json,math,statistics as st,tarfile
from pathlib import Path

R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
backends=['original','ort_cached','ort_simple','direct','direct_avx2','sofie','sofie_gemv','lwtnn','lwtnn_double','direct_blocked']
out={'isolated':{},'integrated':{},'physics':{},'profiles':{}}
for p in sorted((R/'profiles').glob('*/profile.jsonl')):
    if not (p.parent/'exit-code.txt').exists():continue
    assert (p.parent/'exit-code.txt').read_text().strip()=='0'
    rows=[json.loads(line) for line in p.read_text().splitlines()]
    counts=[sum(row['counts'][i] for row in rows) for i in range(4)]
    ns=[sum(row['nanoseconds'][i] for row in rows) for i in range(4)]
    assert len(set(counts))==1 and counts[0]>0, p
    stages=dict(zip(['input_us','number_us','position_us','selection_us'],
                    [value/counts[0]/1000 for value in ns]))
    stages.update(calls=counts[0],events=5,total_us=sum(ns)/counts[0]/1000)
    out['profiles'][p.parent.name]=stages
for b in backends:
    iso={}
    for pressure in [0,1048576]:
        runs=[]
        for d in sorted((R/'isolated').glob(f'c*/{b}/{pressure}')):
            if not (d/'complete.txt').exists():continue
            x=json.loads((d/'result.json').read_text());x['path']=str(d)
            x['mean_us']=st.mean(x['cycle_us']);x['load']=json.loads((d/'load-start.json').read_text())
            runs.append(x)
        if runs:
            means=[x['mean_us'] for x in runs]
            iso[str(pressure)]={'mean_us':st.mean(means),'sd_us':st.stdev(means) if len(means)>1 else None,'runs':runs}
    if iso:out['isolated'][b]=iso
    runs=[]
    for d in sorted((R/'integrated').glob(f'c*/{b}')):
        if not (d/'complete.txt').exists():continue
        assert (d/'exit-code.txt').read_text().strip()=='0'
        assert 'runArgs.threads = 0' in (d/'runargs.RAWtoALL.py').read_text()
        with tarfile.open(d/'perfmonmt_RAWtoALL.json.tar.gz') as t:
            p=json.load(t.extractfile(t.getmembers()[0]))
        components=p['componentLevel']['Execute'];count=components['ActsTrackFindingAlg']['count']
        assert count==p['summary']['nEvents']-1
        x={'path':str(d),'cycle':d.parent.name,'events':p['summary']['nEvents'],'timed_events':count,
           'load':json.loads((d/'load-start.json').read_text()),
           'ckf_ms':components['ActsTrackFindingAlg']['cpuTime']/count,
           'control_ms':components['ActsPixelClusterizationAlg']['cpuTime']/count,
           'event_ms':p['summary']['snapshotLevel']['Execute']['dCPU']/count,
           'event_wall_ms':p['summary']['snapshotLevel']['Execute']['dWall']/count,
           'first_event_ms':p['summary']['snapshotLevel']['FirstEvent']['dCPU'],
           'peak_rss_mib':p['summary']['peaks']['rssPeak']/1024}
        runs.append(x)
    if runs:
        out['integrated'][b]={'runs':runs,'summary':{k:{'mean':st.mean(x[k] for x in runs),'sd':st.stdev(x[k] for x in runs) if len(runs)>1 else None} for k in ['ckf_ms','control_ms','event_ms','event_wall_ms','first_event_ms','peak_rss_mib']}}

for b,entry in out['integrated'].items():
    reference={x['cycle']:x for x in out['integrated'].get('original',{}).get('runs',[])}
    entry['comparisons']={}
    for field in ['ckf_ms','event_ms']:
        ratios=[x[field]/x['control_ms']/(reference[x['cycle']][field]/reference[x['cycle']]['control_ms']) for x in entry['runs'] if x['cycle'] in reference]
        if ratios:entry['comparisons'][field]={'normalized_ratio':st.mean(ratios),'sd_ratio':st.stdev(ratios) if len(ratios)>1 else None,'cycle_ratios':ratios}

def read(path):
    events={};truth={};records=[]
    with gzip.open(path,'rt') as f:
        for line in f:
            records.append(line.strip());x=line.split()
            if x[0]=='E':events[tuple(map(int,x[1:3]))]=list(map(int,x[3:]))
            elif x[0]=='T':truth[tuple(map(int,x[1:4]))]=(int(x[14])>0,float(x[6]))
    return events,truth,records

for sample in ['integrated','physics']:
    base=R/sample/'c1/original/outcomes.txt.gz'
    if not base.exists():continue
    be,bt,br=read(base)
    results={}
    for b in backends:
        p=R/sample/'c1'/b/'outcomes.txt.gz'
        if not p.exists():continue
        e,t,records=read(p);assert e.keys()==be.keys() and t.keys()==bt.keys()
        for key in t:assert t[key][1]==bt[key][1]
        counts=dict(zip(['truth','matched','duplicate_truth','reco','fakes','half'],map(sum,zip(*e.values()))))
        counts.update(events=len(e),efficiency_pct=100*counts['matched']/counts['truth'],fake_pct=100*counts['fakes']/counts['reco'],
                      gained=sum(t[k][0] and not bt[k][0] for k in t),lost=sum(bt[k][0] and not t[k][0] for k in t),
                      exact_sorted_records_equal=sorted(records)==sorted(br))
        groups=collections.defaultdict(lambda:[0,0])
        for key in t:groups[key[:2]][0]+=1;groups[key[:2]][1]+=int(t[key][0])-int(bt[key][0])
        n=counts['truth'];m=len(e);delta=(counts['gained']-counts['lost'])/n
        counts['efficiency_change_pp']=delta*100
        counts['paired_ci95_pp']=196*math.sqrt(sum((d-delta*w)**2 for w,d in groups.values())*m/(m-1)/n**2) if m>1 else None
        results[b]=counts
    out['physics'][sample]=results
(R/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
for b,v in out['isolated'].items():print('isolated',b,{k:round(x['mean_us'],3) for k,x in v.items()})
for b,v in out['integrated'].items():print('integrated',b,v['summary']['ckf_ms'],v['comparisons'])
for sample,rows in out['physics'].items():
    for b,v in rows.items():print('physics',sample,b,v['efficiency_pct'],v['fake_pct'],'gained/lost',v['gained'],v['lost'])
