#include <TTree.h>
#include <TFile.h>
#include <TCanvas.h>

// stolen from https://twiki.cern.ch/twiki/pub/Atlas/ACTS-ITkDocumentation/CheckMaterial.cpp
void makeEtaLines(double zMin, double zMax, double rMax) {
  // Draw pseudorapidity lines
  std::vector<double> etas = {};
  for (int bin = 0; bin < 41; ++bin) {
    etas.push_back(-4.0+bin*0.2);
  }

  for (auto& eta : etas) {
    double z_max = eta >= 0 ? zMax : zMin;
    double r_max = rMax;

    double theta = 2*std::atan(std::exp(-eta));
    r_max = eta != 0 ? z_max*std::tan(theta) : rMax;

    if (r_max >= rMax) {
      r_max = rMax;
      z_max = eta != 0 ? r_max/std::tan(theta) : 0;
    }

    TLine* track = new TLine(0., 0., z_max, r_max);

    if ((int)std::abs(eta*10) % 10 == 0) {
      track->SetLineColor(kBlack);
    } else {
      track->SetLineColor(17);
      track->SetLineStyle(7);}

      track->Draw("same");
  }
}

void plotXY(TFile* file, TTree* tree) {
  file->cd();

  tree->Draw("mat_y:mat_x>>h1(2000,-1300,1300,2000,-1300,1300)", "mat_Z==14 && abs(v_eta)<=1 && Sum$(mat_Z==14)==12", "goff", 100000, 0);
  tree->Draw("mat_y:mat_x>>h2(2000,-1300,1300,2000,-1300,1300)", "mat_Z==14 && abs(v_eta)<=1 && Sum$(mat_Z==14)==13", "goff", 100000, 0);
  tree->Draw("mat_y:mat_x>>h3(2000,-1300,1300,2000,-1300,1300)", "mat_Z==14 && abs(v_eta)<=1 && Sum$(mat_Z==14)>=14", "goff", 100000, 0);

  auto h1 = (TH1*)file->Get("h1");
  auto h2 = (TH1*)file->Get("h2");
  auto h3 = (TH1*)file->Get("h3");
  h1->SetDirectory(0);
  h2->SetDirectory(0);
  h3->SetDirectory(0);

  h1->SetMarkerColor(kRed);
  h1->SetMarkerStyle(7);
  h2->SetMarkerColor(kBlue);
  h2->SetMarkerStyle(7);
  h3->SetMarkerStyle(6);

  h3->Draw("same");
  h2->Draw("same");
  h1->Draw("same");
}

void plotRZ(TFile* file, TTree* tree) {
  file->cd();

  tree->Draw("sqrt(mat_x*mat_x+mat_y*mat_y):mat_z>>h1(6000,-3500,3500,1500,0,1200)", "mat_Z==14 && Sum$(mat_Z==14)<10", "goff", 100000, 0);
  tree->Draw("sqrt(mat_x*mat_x+mat_y*mat_y):mat_z>>h2(6000,-3500,3500,1500,0,1200)", "mat_Z==14 && Sum$(mat_Z==14)>=12", "goff", 100000, 0);

  auto h1 = (TH1*)file->Get("h1");
  auto h2 = (TH1*)file->Get("h2");
  h1->SetDirectory(0);
  h2->SetDirectory(0);

  h1->SetMarkerColor(kRed);
  h1->SetMarkerStyle(7);
  h2->SetMarkerStyle(6);

  h2->Draw("same");
  h1->Draw("same");
}

void plot_material_tracks() {
  auto inputGeant4 = TFile::Open("geant4_material_tracks.root");
  auto inputActs = TFile::Open("acts_material_tracks.root");

  auto tracksGeant4 = (TTree*)inputGeant4->Get("material-tracks");
  auto tracksActs = (TTree*)inputActs->Get("material-tracks");

  auto c1 = new TCanvas();
  plotXY(inputGeant4, tracksGeant4);

  auto c2 = new TCanvas();
  plotXY(inputActs, tracksActs);

  auto c3 = new TCanvas();
  plotRZ(inputGeant4, tracksGeant4);
  makeEtaLines(-3500, 3500, 1300);

  auto c4 = new TCanvas();
  plotRZ(inputActs, tracksActs);
  makeEtaLines(-3500, 3500, 1300);

  auto c5 = new TCanvas();
  tracksGeant4->Draw("Sum$(mat_Z==14):v_phi", "", "prof", 100000, 0);

  inputGeant4->cd();
  auto c6 = new TCanvas();
  tracksGeant4->Draw("Sum$(mat_Z==14):v_eta>>p1", "", "prof prof", 100000, 0);
  tracksActs->Draw("Sum$(mat_Z==14):v_eta>>p2", "", "prof goff", 100000, 0);
  auto p1 = (TProfile*)inputGeant4->Get("p1");
  auto p2 = (TProfile*)inputGeant4->Get("p2");
  p1->SetDirectory(0);
  p2->SetDirectory(0);
  p1->SetMarkerColor(kRed);
  p1->SetLineColor(kRed);
  p1->Draw("same");
  p2->Draw("same");
  auto l4 = new TLegend();
  l4->AddEntry(p1, "Geant4");
  l4->AddEntry(p2, "Acts");
  l4->Draw();

  inputGeant4->Close();
  inputActs->Close();
}
