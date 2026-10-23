#!/usr/bin/env python3
import json
import textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
R=Path.home()/'cern/notes/acts/notebook/2026-10-10_gx2f-energy-loss-validation'
D=json.loads((R/'summary.json').read_text()); rows=D['rows']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2,'figure.dpi':130,'savefig.bbox':'tight','pdf.fonttype':42,'axes.titlesize':11})
colors={'off':'#717882','mean_1':'#2f6aa6','mode_1':'#c25e12','mean_3':'#278165'}
labels={'off':'Energy loss off','mean_1':'Mean · 1 material update','mode_1':'Mode · 1 material update','mean_3':'Mean · 3 material updates'}
figures=[]
def series(truth,thickness,fit):return sorted((r for r in rows if r['truth']==truth and r['thickness_mm']==thickness and r['fit']==fit and r['charge']==0),key=lambda r:r['p_GeV'])
def save(fig,name,footer):
 fig.set_layout_engine('constrained',rect=(0,.085,1,.915))
 fig.text(.5,.018,'\n'.join(textwrap.wrap(footer,125)),ha='center',fontsize=8,color='#555555')
 fig.savefig(R/'plots'/f'{name}.pdf');fig.savefig(R/'plots'/f'{name}.png',dpi=155);figures.append(fig)
fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
for col,thickness in enumerate([5,50]):
 for row,fits in enumerate([['off','mean_1','mode_1'],['mean_1','mode_1']]):
  ax=axes[row,col]
  for fit in fits:
   a=series('bethe_deterministic',thickness,fit)
   ax.errorbar([r['p_GeV'] for r in a],[r['bias_pct'] for r in a],yerr=[r['bias_se_pct'] for r in a],marker='o',capsize=3,lw=1.6,label=labels[fit],color=colors[fit])
  ax.axhline(0,color='black',lw=.7);ax.set(xscale='log',xticks=[1,2,5,10],xticklabels=['1','2','5','10'],ylabel=r'Mean relative $q/p$ error [%]',xlabel='Initial momentum [GeV]',title=f'3 × {thickness} mm silicon'+(' · corrected fits' if row else ''))
  if col==0:ax.legend(fontsize=8)
fig.suptitle('Independent deterministic Bethe truth: energy loss removes the momentum bias',fontsize=13)
save(fig,'01_energy_loss_bias','7 planes · 0.3 T · charged pions · both signs · 2,000 tracks per point · error bars: ±1 standard error; successful fits')
fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
for name in ['truth','off','mean_1','mode_1','mean_3']:
 a=[r for r in D['profile'] if r['series']==name]
 ax.step([r['x_m'] for r in a],[r['qop'] for r in a],where='post',label='Truth (Bethe)' if name=='truth' else labels[name],color='black' if name=='truth' else colors[name],lw=2 if name=='truth' else 1.5,ls='--' if name=='mean_3' else '-')
for x in [2,4,6]:ax.axvspan(x-.05,x+.05,color='#999999',alpha=.15)
ax.set(xlabel='Plane x [m]',ylabel=r'Post-surface $q/p$ [GeV$^{-1}$]',title='Energy-loss profile · 2 GeV positive pion · 3 × 50 mm silicon');ax.legend(fontsize=9)
save(fig,'02_momentum_profile','One fixed-seed event; post-material states are compared at the same planes. Shaded bands mark material surfaces.')
fig,axes=plt.subplots(1,2,figsize=(10,4.8),layout='constrained')
for ax,truth,title in zip(axes,['mean_gaussian','mean_gaussian_scattering'],['Straggling only','Straggling and scattering']):
 edges=np.asarray(D['hist_edges']);center=(edges[:-1]+edges[1:])/2
 for fit in ['mean_1','mean_3']:
  r=next(r for r in rows if r['truth']==truth and r['thickness_mm']==50 and r['p_GeV']==1 and r['charge']==0 and r['fit']==fit)
  ax.stairs(r['hist_density'],edges,color=colors[fit],lw=1.8,label=f"{labels[fit]}\nμ={r['pull_mean']:.3f}, s={r['pull_std']:.3f}, N={r['n_ok']}")
 z=np.linspace(-6,6,400);ax.plot(z,np.exp(-z*z/2)/np.sqrt(2*np.pi),color='black',ls=':',label='Standard normal')
 ax.set(xlabel=r'Sign-aligned $q/p$ pull',ylabel='Probability density',title=title,xlim=(-5,5));ax.legend(fontsize=8)
fig.suptitle('Gaussian model closure · 1 GeV · 3 × 50 mm silicon',fontsize=13)
save(fig,'03_pull_distributions','Pull = sign(q) × (fitted q/p − truth q/p) / fitted σ(q/p). Histogram normalization includes all successful fits.')
fig,axes=plt.subplots(2,2,figsize=(10,7.6),layout='constrained')
for col,(truth,title) in enumerate([('mean_gaussian','Straggling only'),('mean_gaussian_scattering','Straggling and scattering')]):
 for thickness,fit,ls,marker in [(5,'mean_1',':','s'),(50,'mean_1','-','o'),(50,'mean_3','--','^')]:
  a=series(truth,thickness,fit);xs=[r['p_GeV'] for r in a];ys=np.asarray([r['pull_std'] for r in a]);c=colors[fit];label=f'{thickness} mm/slab · '+('1 update' if fit=='mean_1' else '3 updates')
  axes[0,col].errorbar(xs,ys,yerr=[ys-np.asarray([r['pull_std_lo'] for r in a]),np.asarray([r['pull_std_hi'] for r in a])-ys],color=c,linestyle=ls,marker=marker,capsize=3,label=label)
  axes[1,col].plot(xs,[r['mean_chi2_ndof'] for r in a],color=c,linestyle=ls,marker=marker,label=label)
 axes[0,col].set(title=title,ylabel='Pull standard deviation');axes[0,col].axhspan(.9,1.1,color='#777777',alpha=.08)
 axes[1,col].set(ylabel=r'Mean $\chi^2$/9',yscale='log',ylim=(.8,15));axes[0,col].legend(fontsize=8)
 for ax in axes[:,col]:ax.axhline(1,color='black',lw=.8);ax.set(xscale='log',xticks=[1,2,5,10],xticklabels=['1','2','5','10'],xlabel='Initial momentum [GeV]')
fig.suptitle('Material iteration count controls closure in the thick-material sample',fontsize=13)
save(fig,'04_uncertainty_and_fit_quality','2,000 tracks/point, before failures; width bars: normal-theory 95% intervals. Statistical ndf = 14 measurements − 5 fitted bound parameters.')
if (R/'matrix.csv').exists():
 m=np.genfromtxt(R/'matrix.csv',names=True,delimiter=',');fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
 for key,label,color in [('unscaled_error','Unscaled QR','#c25e12'),('equilibrated_error','Equilibrated solve','#2f6aa6'),('covariance_error','Equilibrated covariance','#278165')]:
  xs=np.unique(m['diagonal_decades']);ys=[np.median(m[m['diagonal_decades']==d][key]) for d in xs];upper=[np.quantile(m[m['diagonal_decades']==d][key],.95) for d in xs]
  ax.plot(xs,ys,'o-',color=color,label=label);ax.fill_between(xs,ys,upper,color=color,alpha=.12)
 ax.set(yscale='log',xlabel='Diagonal dynamic range [orders of magnitude]',ylabel='Relative error in scaled coordinates',title='Normal-equation solve and covariance · 18 parameters · 200 matrices per point');ax.legend()
 save(fig,'05_matrix_equilibration','Random positive-definite systems with controlled unit scaling. Lines: median; shaded bands: median to 95th percentile.')
with PdfPages(R/'plots'/'validation_plots.pdf') as pdf:
 for fig in figures:pdf.savefig(fig,bbox_inches='tight')
print('Wrote',len(figures),'figures and PDF bundle')
