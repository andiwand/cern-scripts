#include <TTree.h>
#include <TFile.h>
#include <TCanvas.h>

void geo_ids() {
  auto input = TFile::Open("root_files/hits.root");
  auto tree = (TTree*)input->Get("hits");

  new TCanvas();
  tree->Draw("sqrt(tx*tx+ty*ty):tz:volume_id", "", "", 100000, 0);

  new TCanvas();
  tree->Draw("sqrt(tx*tx+ty*ty):tz:layer_id", "", "", 100000, 0);

  input->Close();
}
