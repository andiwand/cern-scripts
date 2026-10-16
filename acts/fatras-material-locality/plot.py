"""Scientific PDF of material-locality controls and exact G4 photon attribution."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--preview',action='store_true');a=p.parse_args();w=a.work
birth=json.loads((w/'birth-geometry.json').read_text());photon=json.loads((w/'observer-summary.json').read_text())['means'];probe=json.loads((w/'probe-summary.json').read_text());setup=json.loads((w/'probe-input/probes.json').read_text())
plt.rcParams.update({'pdf.fonttype':42,'font.size':10})
a.output.parent.mkdir(parents=True,exist_ok=True)

def save(pdf,fig,note):
 fig.text(.035,.025,note,fontsize=9);fig.tight_layout(rect=[0,.15,1,.94]);pdf.savefig(fig)
 if a.preview:fig.savefig(a.output.with_name(f'page{pdf.get_pagecount()}.png'),dpi=90)
 plt.close(fig)

with PdfPages(a.output) as pdf:
 fig,ax=plt.subplots(1,2,figsize=(13,8));fig.suptitle('Material mapping displaces soft-electron production away from sensors')
 surf=json.loads((w/'surfaces.json').read_text())['entries']
 for s in surf:
  if s['volume']!=17 or s['layer']!=2:continue
  v=s['value'];rot=np.array(v['transform']['rotation']).reshape(3,3);c=np.array(v['transform']['translation']);b=v['bounds']['values']
  if abs(c[2]+36.25)>1e-5:continue
  ends=np.array([c+b[0]*rot[:,0],c+b[2]*rot[:,0]])
  ax[0].plot(ends[:,0],ends[:,1],color='#4c78a8',lw=3)
 theta=np.linspace(-.35,.35,300);ax[0].plot(39.3607069*np.cos(theta),39.3607069*np.sin(theta),'--',color='#f58518',label='Mapped material cylinder')
 pos=np.array(setup['sensor']['value']['transform']['translation'])[:2];pos*=39.36/np.linalg.norm(pos)
 diameter=2*math.sqrt(1*(1+2*.51099895))/(.299792458*2)
 ax[0].add_patch(Circle(pos,diameter,fill=False,ec='#e45756',ls=':',lw=2,label='1 MeV e− maximum transverse displacement'))
 ax[0].plot(*pos,'o',color='#e45756');ax[0].plot([],[],color='#4c78a8',lw=3,label='Physical sensor midplanes')
 ax[0].set(xlim=(28,45),ylim=(-11,11),xlabel='x [mm]',ylabel='y [mm]',title='First pixel barrel layer, 2 T');ax[0].set_aspect('equal');ax[0].legend(fontsize=8,loc='upper left')
 bins=birth['runs']['Fatras']['bins'][1:];labels=['0.1–0.2','0.2–0.423','0.423–1','1–5','5–20','≥20']
 ax[1].bar(labels,[100*x['dxy_gt_diameter']/x['n'] for x in bins],color='#4c78a8');ax[1].tick_params(axis='x',rotation=30);ax[1].set(ylabel='Births with sensor distance > orbit diameter [%]',xlabel='Electron birth kinetic energy [MeV]',ylim=(0,110),title='Retained Fatras ionisation births in pixel-barrel envelope')
 save(pdf,fig,'Geometry diagnostic: 25 < birth r < 190 mm, |birth z| < 510 mm; no occupancy selection. Three ttbar + PU200 events.\nAll 73,273 retained 0.1–1 MeV ionisation births in this envelope fail the transverse vacuum reachability bound.\nMedian transverse distance to any pixel sensor is 5.83 mm. Longitudinal sensor bounds are ignored: this is a conservative veto.\nNo sensitive surface has material in the current map; 123 non-sensitive surfaces carry the mapped material.')

 fig,ax=plt.subplots(1,2,figsize=(13,8));fig.suptitle('Controlled electron starts separate production locality from stopping')
 energies=[.1,.3,1,3,10];styles=[('probe-fatras','Fatras, existing map','#4c78a8','o-'),('probe-vacuum','Fatras, transport only','#72b7b2','s--'),('probe-geant4-observed','Geant4, physical ODD','#f58518','^-')]
 for axt,origin,title in zip(ax,['sensor','mapped-cylinder'],['Starts 1 μm from sensor midplane (inside physical silicon)','Starts on mapped cylinder at r=39.36 mm']):
  for name,label,color,style in styles:
   vals=[probe[name][str(e)+':'+origin]['hits']/240 for e in energies]
   axt.plot(energies,vals,style,color=color,label=label)
  axt.set_xscale('log');axt.set_xticks(energies,[str(x) for x in energies]);axt.set(xlabel='Initial electron kinetic energy [MeV]',ylabel='Primary hits / input electron',title=title);axt.legend(fontsize=8)
 save(pdf,fig,'2400 fixed electron probes: 240 per energy/origin, same momenta for each origin; all primary hits counted.\nAt 100 keV: sensor starts give Fatras 1540 hits vs G4 240; mapped starts give zero in both.\nFatras full physics and transport-only agree at ≤1 MeV: sensor crossings have no local material loss in this map.\nNumerical Fatras uses 4 turns / 5 mm, p≥0.2 MeV, pT≥0.05 MeV. Transport-only run has 11 step-cap failures; full-physics run has none.')

 fig,ax=plt.subplots(1,2,figsize=(13,8));fig.suptitle('Exact missing photon channels in the inclusive G4 reference')
 labels=['Pixel','Strip','All ID'];x=np.arange(3)
 for i,(code,label,color) in enumerate([('compt','Compton','#4c78a8'),('phot','Photoelectric','#f58518')]):
  vals=[photon[r+'_creator'][code] for r in ['pixel','strip','ID']]
  ax[0].bar(x+(i-.5)*.35,vals,.35,label=label,color=color)
 ax[0].set_xticks(x,labels);ax[0].set_ylabel('Secondary hits/event');ax[0].legend()
 for i,(field,label,color) in enumerate([('creator','All hits','#999999'),('born_sensitive','Born in sensitive silicon','#4c78a8'),('parent_below_pair_threshold','Parent photon born below 1.022 MeV','#f58518')]):
  vals=[photon['ID_'+field][code] for code in ['compt','phot']]
  ax[1].bar(np.arange(2)+(i-1)*.25,vals,.25,label=label,color=color)
 ax[1].set_xticks([0,1],['Compton','Photoelectric']);ax[1].set_ylabel('Secondary hits/event');ax[1].legend(fontsize=8)
 save(pdf,fig,'3 matched ttbar + fixed PU200 events, 2 T; inclusive G4 FTFP_BERT, physically confined to ODD ID; no analysis cuts.\nObservational callbacks reproduce all six reference hit/particle CSVs byte-for-byte and all secondary hit counts exactly.\nCompton: 6283 hits/event; photoelectric: 1949.3. The two subsets on the right overlap and must not be added.\n99.8% of photoelectric hits are from electrons born in sensitive silicon. 4420 photon-electron hits have parent birth E<1.022 MeV.')

 fig,ax=plt.subplots(figsize=(13,8));fig.suptitle('G4 default production thresholds differ from a fixed 100 keV electron cut')
 cuts=list(csv.DictReader((w/'geant4-observed/observer.tsv.cuts.tsv').open(),delimiter='\t'))
 ax.bar([r['material'] for r in cuts],[float(r['electron_cut_MeV'])*1000 for r in cuts],color='#4c78a8');ax.axhline(100,color='#f58518',ls='--',label='Current Fatras ionisation production threshold')
 ax.set(ylabel='Electron production threshold [keV]',xlabel='Material');ax.legend();ax.tick_params(axis='x',rotation=30)
 save(pdf,fig,'Thresholds read from the initialized G4 material/cuts couples; default physics unchanged.\nSilicon: 423.34 keV; copper: 1034.03 keV; carbon foam: 112.52 keV. These are production thresholds, not tracking kills.\nDo not replace every Fatras material threshold with the silicon value. Geometry-averaged material loses composition/locality.\nReference CPU remains main 0.790, accepted numerical Fatras 11.388, G4 38.994 s/event (previous measurement campaigns).\nThis study adds diagnostics and controlled probes; it does not establish a new inclusive physics or CPU result.')
print(a.output)
