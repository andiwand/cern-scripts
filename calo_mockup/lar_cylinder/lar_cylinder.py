import pyg4ometry
import math
import numpy as np

idMat = np.eye(3)
idRot = pyg4ometry.transformation.matrix2tbxyz(idMat)

mAir = pyg4ometry.geant4.nist_material_2geant4Material("G4_AIR")
mLAr = pyg4ometry.geant4.nist_material_2geant4Material("G4_lAr")

reg = pyg4ometry.geant4.Registry()

solidWorld = pyg4ometry.geant4.solid.Box("World_solid", 50000, 50000, 50000, reg)
logWorld = pyg4ometry.geant4.LogicalVolume(solidWorld, mAir, "world", reg)

reg.setWorld(logWorld.name)

solidLar = pyg4ometry.geant4.solid.Tubs(
    "LAr_solid", 1000, 2000, 10000, 0, 2 * math.pi, reg
)
logLar = pyg4ometry.geant4.LogicalVolume(solidLar, mLAr, "LAr_log", reg)
physLar = pyg4ometry.geant4.PhysicalVolume(
    idRot, [0, 0, 0], logLar, "LAr_phys", logWorld, reg
)

# Visualiztion options
voAir = pyg4ometry.visualisation.VisualisationOptions()
voAir.visible = False

voCu = pyg4ometry.visualisation.VisualisationOptions()
voCu.colour = [0.3, 0.5, 1.0]
voCu.alpha = 1.0

v = pyg4ometry.visualisation.VtkViewerColoured(defaultColour="random")
v.addMaterialVisOption("G4_AIR", voAir)

# Obj write out
v.addLogicalVolume(logWorld)
v.exportOBJScene("lar_cylinder")
v.addAxes(2000)
v.view()

# GDML wirte out
w = pyg4ometry.gdml.Writer()
w.addDetector(reg)
w.write("lar_cylinder.gdml")
