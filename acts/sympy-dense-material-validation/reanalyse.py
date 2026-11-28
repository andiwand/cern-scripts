import sys
from pathlib import Path
import numpy as np
import scipy.optimize
import scipy.stats
import uproot
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path(__file__).parent
base=Path('/Users/andreas/cern/thesis/data/dense-propagation')
sys.path.insert(0,'/Users/andreas/cern/thesis/scripts/dense-propagation')
from legacy_common import robust_gauss_fit
mass=.1056583755
rows=[]
def amplitude_fit(data):
  # Same windowing as the historical fitter, but fit the normalization too.
  for _ in range(3):
    lo,hi=np.percentile(data,[1,99])
    hist,edges=np.histogram(data,bins=30,range=(lo,hi),density=True)
    centers=(edges[:-1]+edges[1:])/2
    def gauss(x,amp,mean,sigma):return amp*np.exp(-.5*((x-mean)/sigma)**2)
    pars,_=scipy.optimize.curve_fit(gauss,centers,hist,p0=(hist.max(),np.median(data),np.std(data)),bounds=([0,-np.inf,1e-12],[np.inf,np.inf,np.inf]))
    _,m,s=pars
    data=data[np.abs(data-m)<3*s]
  return s

fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=True)
for row,material in enumerate(['fe','lar']):
  for col,thickness in enumerate([10,100,1000]):
    a=np.genfromtxt(base/'acts'/f'msc_eloss_{material}_{thickness}mm.csv',names=True,delimiter=',')
    with uproot.open(base/'geant4'/f'logscale_mom_{material}_{thickness}mm.root') as f:
      g=f['reading'].arrays(library='np')
    kinetic=g['p_initial']
    momentum=np.sqrt(kinetic*(kinetic+2*mass))
    pf=np.sqrt(g['p_final']*(g['p_final']+2*mass))
    valid=np.isfinite(a['x_sigma'])&(a['x_sigma']>0)
    # Compare against ACTS at each event's initial momentum. This avoids
    # conflating the kinetic-energy correction with unequal bin populations.
    def interp(field,p): return np.interp(p,a['p_initial'][valid],a[field][valid])
    bins=np.geomspace(2,300,18)
    old=[];fixed=[];fitfixed=[];centers=[]
    for lo,hi in zip(bins[:-1],bins[1:]):
      sel=(momentum>=lo)&(momentum<hi)&(pf>2)&(momentum>a['p_initial'][valid][0])
      if np.count_nonzero(sel)<100: continue
      x=g['x'][sel]
      old_z=x/interp('x_sigma',kinetic[sel])
      fixed_z=x/interp('x_sigma',momentum[sel])
      (_,old_s),_=robust_gauss_fit(old_z)
      (_,fixed_s),_=robust_gauss_fit(fixed_z)
      fitted_s=amplitude_fit(fixed_z)
      centers.append(np.sqrt(lo*hi)); old.append(old_s); fixed.append(fixed_s)
      fitfixed.append(fitted_s)
      # Energy loss uses all primary screen crossings in this momentum bin,
      # without the scattering plot's outgoing-momentum cut.
      esel=(momentum>=lo)&(momentum<hi)&(momentum>a['p_initial'][valid][0])
      loss=g['e_loss'][esel]
      pred=interp('e_loss',momentum[esel])
      rows.append(dict(material=material,thickness_mm=thickness,p_low=lo,p_high=hi,n_msc=len(x),msc_old=old_s,msc_corrected=fixed_s,msc_corrected_free_amplitude=fitted_s,n_eloss=len(loss),eloss_ratio=loss.mean()/pred.mean(),eloss_ratio_sem=loss.std()/np.sqrt(len(loss))/pred.mean()))
    ax=axes[row,col]
    ax.plot(centers,old,'o-',label='Treat stored kinetic energy as p')
    ax.plot(centers,fixed,'o-',label='Convert kinetic energy to p')
    ax.plot(centers,fitfixed,'o-',label='Also fit Gaussian normalization')
    ax.axhline(1,c='k',lw=.8)
    ax.set_title(f'{material.upper()}, {thickness} mm')
    ax.set_xscale('log');ax.set_ylim(.85,1.15); ax.grid(alpha=.2)
    ax.set_ylabel('Core width of x / ACTS predicted sigma')
    if row==1: ax.set_xlabel('True initial momentum [GeV]')
axes[0,0].legend(fontsize=8)
fig.suptitle('Saved thesis Geant4 events: comparison corrections\nSame events before/after; outgoing true momentum > 2 GeV; ACTS evaluated at each event momentum')
fig.tight_layout();fig.savefig(out/'historical-comparison.png',dpi=160);fig.savefig(out/'historical-comparison.pdf')
with open(out/'historical-comparison.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print('Representative saved-data results (core widths are G4 / ACTS):')
for r in rows:
 if r['thickness_mm']==1000 and (3<r['p_low']<4 or 9<r['p_low']<13 or 90<r['p_low']<120): print(r)
mode=scipy.optimize.minimize_scalar(lambda x:-scipy.stats.landau.pdf(x),bounds=(-2,2),method='bounded').x
print('SciPy standardized Landau mode:',mode,'so fitted loc is not the mode.')
rng=np.random.default_rng(20261031)
x=rng.normal(size=1000000)
print('Gaussian fitter control, known sigma=1:', 'sample sigma',x.std(),'historical fit',robust_gauss_fit(x)[0][1],'free-amplitude fit',amplitude_fit(x))
