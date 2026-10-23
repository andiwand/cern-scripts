from pathlib import Path
import acts,acts.examples,acts.root,acts.examples.json
from acts.examples.odd import getOpenDataDetector
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work',type=Path,required=True)
args=parser.parse_args()
root=args.work
root.mkdir(parents=True,exist_ok=True)
material=acts.root.RootMaterialDecorator(fileName=str(Path.home()/'cern/scripts/acts/fatras-realism/fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root'),level=acts.logging.WARNING)
detector=getOpenDataDetector(materialDecorator=material,buildCalorimeter=False,buildMuonSystem=False,logLevel=acts.logging.WARNING)
s=acts.examples.Sequencer(events=1,numThreads=1,logLevel=acts.logging.INFO)
s.addWriter(acts.examples.json.JsonSurfacesWriter(trackingGeometry=detector.trackingGeometry(),outputDir=str(root),writeSensitive=True,writeApproach=False,writeLayer=False,writeBoundary=False,level=acts.logging.INFO))
s.run()
(root/'detector.csv').replace(root/'surfaces.json')
import json
context=acts.GeometryContext.dangerouslyDefaultConstruct()
rows=[]
def record(surface):
 if surface.surfaceMaterial is not None:
  rows.append({'id':surface.geometryId.value,'volume':surface.geometryId.volume,'layer':surface.geometryId.layer,'approach':surface.geometryId.approach,'sensitive':surface.geometryId.sensitive,'center':list(surface.center(context)),'description':surface.toString(context),'material':surface.surfaceMaterial.toString().splitlines()[0]})
detector.trackingGeometry().visitSurfaces(record,False)
(root/'material-surfaces.json').write_text(json.dumps(rows,indent=2))
