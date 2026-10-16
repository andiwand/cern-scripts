"""PDF diagnosis of the inclusive secondary-hit gap; no analysis cuts."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work',type=Path,required=True)
p.add_argument('--reference',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--preview',action='store_true',help='Also render PNG pages for layout inspection')
a=p.parse_args()
s=json.loads((a.work/'summary.json').read_text())
v=json.loads((a.work/'sensitivity.json').read_text())['runs']
v.update(json.loads((a.work/'loops16.json').read_text())['runs'])
ref=json.loads(a.reference.read_text())
f=s['runs']['Fatras']['mean'];g=s['runs']['Geant4']['mean']
procs=['5','2','6','1','4'];names=['Ionisation','Conversion','Other','Decay','Nuclear']
colors=['#4c78a8','#f58518','#e45756','#72b7b2','#b279a2']
vols=['16','17','18','23','24','25','28','29','30']
volnames=['Pixel EC−','Pixel barrel','Pixel EC+','Inner strip EC−','Inner strip barrel','Inner strip EC+','Outer strip EC−','Outer strip barrel','Outer strip EC+']
plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
footer='3 matched ttbar + fixed PU200 events, 2 T; all written hits, no analysis momentum/time cuts.\nGeant4 default FTFP_BERT, physical ODD ID only (r < 1202 mm, |z| < 4002 mm).'

def mean(run,region='ID'):
    return run['mean'][region+'_totals']['secondary']

def hist(m,region,field,proc):
    return np.array([m[region+'_'+field].get(proc+':'+str(i),0) for i in range(len(s['edges'][field])+1)])

def bins(field):
    edges=s['edges'][field]
    return [f'<{edges[0]:g}']+[f'{x:g}–{y:g}' for x,y in zip(edges,edges[1:])]+[f'≥{edges[-1]:g}']

def pair(ax,labels,first,second,title):
    x=np.arange(len(labels));ax.bar(x-.2,first,.4,label='Fatras numerical',color='#4c78a8');ax.bar(x+.2,second,.4,label='Geant4',color='#f58518')
    ax.set_xticks(x,labels,rotation=35,ha='right');ax.set_title(title);ax.set_ylabel('Secondary hits/event');ax.legend(fontsize=8)

def save(pdf,fig,note):
    fig.text(.035,.025,footer+'\n'+note,fontsize=8)
    fig.tight_layout(rect=[0,.14,1,.95]);pdf.savefig(fig)
    if a.preview: fig.savefig(a.output.with_name(f'page{pdf.get_pagecount()}.png'),dpi=90)
    plt.close(fig)

a.output.parent.mkdir(parents=True,exist_ok=True)
with PdfPages(a.output) as pdf:
    fig,ax=plt.subplots(1,3,figsize=(15,8));fig.suptitle('Remaining secondary-hit gap: totals conceal compensating errors')
    main=ref['summary']['ACTS main']
    x=np.arange(2)
    for shift,values,label,color in [(-.26,[main['pixel_secondary'],main['ID_secondary']-main['pixel_secondary']],'ACTS main 300b664a3d','#999999'),(0,[f['pixel_totals']['secondary'],f['strip_totals']['secondary']],'Fatras numerical','#4c78a8'),(.26,[g['pixel_totals']['secondary'],g['strip_totals']['secondary']],'Geant4','#f58518')]:
        ax[0].bar(x+shift,values,.26,label=label,color=color)
    ax[0].set_xticks(x,['Pixels','Strips']);ax[0].set_ylabel('Secondary hits/event');ax[0].set_title('Inclusive occupancy');ax[0].legend(fontsize=8)
    for axt,region,title in zip(ax[1:],['pixel','ID'],['Pixel deficit','All-ID deficit']):
        diffs=[g[region+'_process'].get(p,0)-f[region+'_process'].get(p,0) for p in procs]
        axt.barh(names,diffs,color=colors);axt.axvline(0,color='k',lw=.7);axt.invert_yaxis();axt.set_title(title);axt.set_xlabel('Geant4 − Fatras hits/event')
        for i,d in enumerate(diffs):axt.text(d,i,f' {d:+,.0f}',va='center',ha='left' if d>=0 else 'right',fontsize=9)
        axt.margins(x=.3)
    save(pdf,fig,'Fatras: 34,581 pixel / 93,639 ID; G4: 38,683 / 114,198. Main (300b664a3d): 5,145 / 11,936.\nCPU s/event: main 0.790 (archived 5 events); optimised Fatras 11.388 (repeat median); G4 38.994. Process = carrier birth tag.')

    fig,ax=plt.subplots(1,2,figsize=(15,8));fig.suptitle('The largest deficit is in the barrel; pixel endcaps already have excess hits')
    pair(ax[0],volnames,[f['ID_volume'][v] for v in vols],[g['ID_volume'][v] for v in vols],'Detector volumes')
    matrix=np.array([[g['ID_volume_process'].get(v+':'+p,0)-f['ID_volume_process'].get(v+':'+p,0) for p in procs] for v in vols])
    lim=abs(matrix).max();im=ax[1].imshow(matrix,cmap='RdBu_r',vmin=-lim,vmax=lim,aspect='auto')
    ax[1].set_xticks(range(5),names,rotation=35,ha='right');ax[1].set_yticks(range(9),volnames)
    for (i,j),value in np.ndenumerate(matrix):ax[1].text(j,i,f'{value:,.0f}',ha='center',va='center',fontsize=8,color='white' if abs(value)>.65*lim else 'black')
    fig.colorbar(im,ax=ax[1],label='Geant4 − Fatras hits/event')
    save(pdf,fig,'Barrel: Fatras 37,504 vs G4 57,003 (34.2% low). Endcaps combined: 56,135 vs 57,195 (1.9% low).\nVolume IDs: pixel 16/17/18, inner strips 23/24/25, outer strips 28/29/30; middle ID is barrel.')

    fig,ax=plt.subplots(2,2,figsize=(14,10));fig.suptitle('Ionisation: missing sensor revisits and a distorted energy/region distribution')
    pair(ax[0,0],bins('birth_ke_MeV'),hist(f,'ID','birth_ke_MeV','5'),hist(g,'ID','birth_ke_MeV','5'),'Hits by electron birth kinetic energy [MeV]')
    pair(ax[0,1],bins('distance_mm'),hist(f,'ID','distance_mm','5'),hist(g,'ID','distance_mm','5'),'Distance from birth to hit [mm]')
    pair(ax[1,0],['Pixel barrel','Pixel ECs','Strip barrels','Strip ECs'],
         [sum(f['ID_volume_process'].get(v+':5',0) for v in group) for group in [['17'],['16','18'],['24','29'],['23','25','28','30']]],
         [sum(g['ID_volume_process'].get(v+':5',0) for v in group) for group in [['17'],['16','18'],['24','29'],['23','25','28','30']]],'Ionisation by region')
    pair(ax[1,1],['Unique carrier–sensor pairs','Additional visits'],[f['ID_carrier_sensors']['5'],f['ID_process']['5']-f['ID_carrier_sensors']['5']],[g['ID_carrier_sensors']['5'],g['ID_process']['5']-g['ID_carrier_sensors']['5']],'Exact accounting of ionisation hits')
    save(pdf,fig,'Ionisation electrons with ≥1 ID hit: Fatras 11,939 vs G4 9,315. Repeated carrier/sensor visits: 231 vs 8,840.\nOnly 1,108 G4 ionisation hits have birth momentum below current transport cuts or birth KE below 100 keV.\nBirth proximity is a diagnostic, not proof of birth in the hit sensor; partitions here overlap and must not be added.')

    fig,ax=plt.subplots(2,2,figsize=(14,10));fig.suptitle('Other electromagnetic channels, conversions and decays')
    for axt,proc,title in [(ax[0,0],'6','Other-process hits by birth kinetic energy [MeV]'),(ax[0,1],'2','Conversion hits by birth kinetic energy [MeV]')]:
        pair(axt,bins('birth_ke_MeV'),hist(f,'ID','birth_ke_MeV',proc),hist(g,'ID','birth_ke_MeV',proc),title)
    labels=['Primary','Radiation','Nuclear','Decay','Other'];codes=['0','3','4','1','6']
    pair(ax[1,0],labels,[f['ID_parent_process'].get('6:'+p,0) for p in codes],[g['ID_parent_process'].get('6:'+p,0) for p in codes],'Other-process hits by parent birth process')
    pair(ax[1,1],['All decay','From μ+','From μ−'],[f['ID_process']['1'],f['ID_parent'].get('1:-13',0),f['ID_parent'].get('1:13',0)],[g['ID_process']['1'],g['ID_parent'].get('1:-13',0),g['ID_parent'].get('1:13',0)],'Decay hit deficit is concentrated in μ+ daughters')
    save(pdf,fig,'8,232 of 8,241 other-process G4 hits are electrons born from photons; subtype was not archived.\nCompton/photoelectric channels are absent in Fatras. 4,992 other-process hits lie within 1 mm of birth; 3,018 fail current birth cuts.\nConversion hits from primary photons: 21,504 vs 24,566. μ+ daughter hits: 1,217 vs 2,969; parent PDG alone does not prove decay at rest.')

    fig,ax=plt.subplots(2,2,figsize=(14,10));fig.suptitle('Transport sensitivity: more turns improve totals but preserve the barrel deficit')
    runs=[s['runs']['Fatras'],v['loops8'],v['loops16'],v['step2p5']]
    labels=['4 turns / 5 mm','8 turns / 5 mm','16 turns / 5 mm','4 turns / 2.5 mm']
    for axt,region,title in [(ax[0,0],'pixel','Pixel secondary hits'),(ax[0,1],'ID','All-ID secondary hits')]:
        axt.bar(labels,[mean(r,region) for r in runs],color='#4c78a8');axt.axhline(g[region+'_totals']['secondary'],color='#f58518',label='Geant4');axt.set_title(title);axt.tick_params(axis='x',rotation=25);axt.set_ylabel('Hits/event');axt.legend()
    for group,name,color in [(['17','24','29'],'Barrel','#4c78a8'),(['16','18','23','25','28','30'],'Endcaps','#72b7b2')]:
        values=[sum(r['mean']['ID_volume'][v] for v in group) for r in runs]
        ax[1,0].plot(range(4),values,'o-',label='Fatras '+name,color=color)
        ax[1,0].axhline(sum(g['ID_volume'][v] for v in group),color=color,ls='--',label='G4 '+name)
    ax[1,0].set_xticks(range(4),labels,rotation=25,ha='right');ax[1,0].set_ylabel('Secondary hits/event');ax[1,0].set_title('Spatial distribution remains wrong');ax[1,0].legend(fontsize=8)
    cpu=[11.3881623]+[r['metadata']['sequencer_cpu_seconds']/r['metadata']['events'] for r in runs[1:]]
    ax[1,1].bar(labels,cpu,color='#4c78a8');ax[1,1].tick_params(axis='x',rotation=25);ax[1,1].set_title('Exploratory CPU cost');ax[1,1].set_ylabel('Process CPU seconds/event')
    for i,x in enumerate(cpu):ax[1,1].text(i,x,f'{x:.2f}',ha='center',va='bottom')
    save(pdf,fig,'No physics, input, acceptance or G4 changes. Single three-event sensitivity runs; baseline CPU is an earlier repeat median.\nChanged random histories: count differences are population sensitivities, not matched recovered hits. No convergence claim.\nAt 16 turns the pixel total is close to G4, but the barrel remains deficient and endcap excess grows. Not adopted as a new reference.')
print(a.output)
