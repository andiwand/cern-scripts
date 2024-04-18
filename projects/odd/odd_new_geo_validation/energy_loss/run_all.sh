#!/usr/bin/env bash

set -e

for pT in 2 10 100
do
  python ./full_chain_nomaterial.py fatras $pT -o ${pT}GeV_fatras_nomaterial
  python ./full_chain_nomaterial.py geant4 $pT -o ${pT}GeV_geant4_nomaterial

  cd ${pT}GeV_fatras_nomaterial
  ActsAnalysisResidualsAndPulls -i trackstates_kalman.root -o residuals_and_pulls.root --predicted --filtered --smoothed --fit-predicted --fit-filtered --fit-smoothed -s
  cd ..

  cd ${pT}GeV_geant4_nomaterial
  ActsAnalysisResidualsAndPulls -i trackstates_kalman.root -o residuals_and_pulls.root --predicted --filtered --smoothed --fit-predicted --fit-filtered --fit-smoothed -s
  cd ..
done
