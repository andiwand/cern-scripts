# generate material tracks Acts
python gdml_material_validation.py

# generate material tracks G4
python gdml_material_recording.py

# process tracks to material composition
./material_composition.sh acts_material_tracks.root acts_material_composition.root
./material_composition.sh geant4_material_tracks.root geant4_material_composition.root

# create material plots
python make_material_plots.py acts_material_composition.root material_plots_acts
python make_material_plots.py geant4_material_composition.root material_plots_geant4

histcmp --label-monitored "acts" --label-reference "geant4" --title "ODD material composition" -o material.html acts_material_composition.root geant4_material_composition.root
