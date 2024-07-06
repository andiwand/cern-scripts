#!/bin/bash

mkdir -p athena_acts_mu100GeV
cd athena_acts_mu100GeV

wget https://atlas-art-data.web.cern.ch/atlas-art-data/grid-output/main/Athena/x86_64-el9-gcc13-opt/2024-06-02T2101/InDetPhysValMonitoring/test_run4_mu100_reco/AOD.root -O AOD.athena.root
wget https://atlas-art-data.web.cern.ch/atlas-art-data/grid-output/main/Athena/x86_64-el9-gcc13-opt/2024-06-02T2101/InDetPhysValMonitoring/test_run4_acts_ckf_mu100GeV/AOD.ambi.root -O AOD.acts.root

runIDPVM.py \
    --filesInput AOD.athena.root \
    --outputFile idpvm.athena.root
runIDPVM.py \
    --filesInput AOD.acts.root \
    --outputFile idpvm.acts.root

# wget https://atlas-art-data.web.cern.ch/atlas-art-data/grid-output/main/Athena/x86_64-el9-gcc13-opt/2024-06-02T2101/InDetPhysValMonitoring/test_run4_mu100_reco/idpvm.root -O idpvm.athena.root
# wget https://atlas-art-data.web.cern.ch/atlas-art-data/grid-output/main/Athena/x86_64-el9-gcc13-opt/2024-06-02T2101/InDetPhysValMonitoring/test_run4_acts_ckf_mu100GeV/idpvm.ambi.root -O idpvm.acts.root

$ATLAS_LOCAL_ROOT/dcube/current/DCubeClient/python/dcube.py \
    -p -x dcube \
    -c ../dcube_ART_IDPVMPlots_ITk.xml \
    -r idpvm.athena.root \
    idpvm.acts.root
