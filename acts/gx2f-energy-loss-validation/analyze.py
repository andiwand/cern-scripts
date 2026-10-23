#!/usr/bin/env python3
import csv,json
from pathlib import Path
import numpy as np
from scipy.stats import chi2 as chi2dist
ROOT=Path.home()/'cern/notes/acts/notebook/2026-10-10_gx2f-energy-loss-validation'
x=np.genfromtxt((ROOT/'tracks.csv' if (ROOT/'tracks.csv').exists() else ROOT/'tracks.csv.gz'),names=True,delimiter=',',dtype=None,encoding='utf8')
rows=[]
edges=np.linspace(-6,6,61)
for truth in np.unique(x['truth']):
 for thickness in np.unique(x[x['truth']==truth]['thickness_mm']):
  for momentum in np.unique(x['p_GeV']):
   for charge in [0,-1,1]:
    for fit in ['off','mean_1','mode_1','mean_3']:
     mask=(x['truth']==truth)&(x['thickness_mm']==thickness)&(x['p_GeV']==momentum)&(x['fit']==fit)
     if charge: mask &= x['charge']==charge
     a=x[mask]; y=a[a['ok']==1]
     pull=y['pull']*y['charge']
     r=dict(truth=str(truth),thickness_mm=float(thickness),p_GeV=float(momentum),charge=charge,fit=fit,n=len(a),n_ok=len(y),failures=int(np.sum(a['ok']==0)),n_bad_cov=int(np.sum(~np.isfinite(y['sigma_qop'])|(y['sigma_qop']<=0))),bias_pct=100*float(np.mean(y['relative_qop_error'])),bias_se_pct=100*float(np.std(y['relative_qop_error'],ddof=1)/np.sqrt(len(y))),pull_mean=float(np.mean(pull)),pull_mean_se=float(np.std(pull,ddof=1)/np.sqrt(len(y))),pull_std=float(np.std(pull,ddof=1)),pull_std_lo=float(np.sqrt((len(y)-1)*np.var(pull,ddof=1)/chi2dist.ppf(.975,len(y)-1))),pull_std_hi=float(np.sqrt((len(y)-1)*np.var(pull,ddof=1)/chi2dist.ppf(.025,len(y)-1))),coverage_1sigma=float(np.mean(np.abs(pull)<=1)),coverage_2sigma=float(np.mean(np.abs(pull)<=2)),mean_chi2_ndof=float(np.mean(y['chi2']/y['ndof'])),chi2_p_lt_001=float(np.mean(chi2dist.sf(y['chi2'],y['ndof'])<.01)),median_us=float(np.median(y['time_us'])),mean_updates=float(np.mean(y['nupdates'])))
     hist,_=np.histogram(pull,bins=edges)
     r['hist_density']=(hist/(len(y)*np.diff(edges))).tolist(); r['hist_underflow']=int(np.sum(pull<edges[0])); r['hist_overflow']=int(np.sum(pull>edges[-1])); rows.append(r)
fields=[k for k in rows[0] if k!='hist_density']
with (ROOT/'summary.csv').open('w') as f:
 w=csv.DictWriter(f,fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
profile=np.genfromtxt(ROOT/'trajectory.csv',names=True,delimiter=',',dtype=None,encoding='utf8')
data=dict(commit='e98eb100aa143d6f320981399f41178c674f0c3a',n_truth=56000,n_fits=len(x),failures=int(np.sum(x['ok']==0)),hist_edges=edges.tolist(),rows=rows,profile=[dict(series=str(p['series']),x_m=float(p['x_m']),qop=float(p['qop'])) for p in profile])
(ROOT/'summary.json').write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
print('fits',len(x),'failures',data['failures'],'bad cov',sum(r['n_bad_cov'] for r in rows if r['charge']==0))
print('truth thick p fit bias% +/-SE pullmean pullstd coverage chi2/ndof')
for r in rows:
 if r['charge']==0 and r['p_GeV'] in [1,2] and r['fit'] in ['off','mean_1','mean_3']:
  print(r['truth'],r['thickness_mm'],r['p_GeV'],r['fit'],*[round(r[k],6) for k in ['bias_pct','bias_se_pct','pull_mean','pull_std','coverage_1sigma','mean_chi2_ndof']])
print('vacuum max abs paired qop diff',max(float(np.max(np.abs(x[(x['truth']=='vacuum')&(x['fit']==f)]['qop_fit']-x[(x['truth']=='vacuum')&(x['fit']=='off')]['qop_fit']))) for f in ['mean_1','mean_3','mode_1']))
