#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# pixel

for i in 2 4; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelInner::Barrel_layer_${i}_grid.csv" \
        "ITkPixelInner::Barrel_layer_${i}_surface_center.csv" \
        -o "ITkPixelInner_Barrel_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36 38 40 42 44 46 48 50 52 54 56 58; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelInner::NegativeEndcap_layer_${i}_grid.csv" \
        "ITkPixelInner::NegativeEndcap_layer_${i}_surface_center.csv" \
        -o "ITkPixelInner_NegativeEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36 38 40 42 44 46 48 50 52 54 56 58; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelInner::PositiveEndcap_layer_${i}_grid.csv" \
        "ITkPixelInner::PositiveEndcap_layer_${i}_surface_center.csv" \
        -o "ITkPixelInner_PositiveEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter::Barrel_layer_${i}_grid.csv" \
        "ITkPixelOuter::Barrel_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_Barrel_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter::NegativeEndcap::Ring0_layer_${i}_grid.csv" \
        "ITkPixelOuter::NegativeEndcap::Ring0_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_NegativeEndcap_Ring0_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter::PositiveEndcap::Ring0_layer_${i}_grid.csv" \
        "ITkPixelOuter::PositiveEndcap::Ring0_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_PositiveEndcap::Ring0_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter::NegativeEndcap::Ring1_layer_${i}_grid.csv" \
        "ITkPixelOuter::NegativeEndcap::Ring1_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_NegativeEndcap_Ring1_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter::PositiveEndcap::Ring1_layer_${i}_grid.csv" \
        "ITkPixelOuter::PositiveEndcap::Ring1_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_PositiveEndcap_Ring1_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter::NegativeEndcap::Ring2_layer_${i}_grid.csv" \
        "ITkPixelOuter::NegativeEndcap::Ring2_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_NegativeEndcap_Ring2_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter::PositiveEndcap::Ring2_layer_${i}_grid.csv" \
        "ITkPixelOuter::PositiveEndcap::Ring2_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_PositiveEndcap_Ring2_layer_${i}_surface_grid.pdf"
done

# strips

for i in 2 4 6 8; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkStrip::Barrel_layer_${i}_grid.csv" \
        "ITkStrip::Barrel_layer_${i}_surface_center.csv" \
        -o "ITkStrip_Barrel_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkStrip::NegativeEndcap_layer_${i}_grid.csv" \
        "ITkStrip::NegativeEndcap_layer_${i}_surface_center.csv" \
        -o "ITkStrip_NegativeEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkStrip::PositiveEndcap_layer_${i}_grid.csv" \
        "ITkStrip::PositiveEndcap_layer_${i}_surface_center.csv" \
        -o "ITkStrip_PositiveEndcap_layer_${i}_surface_grid.pdf"
done

# hgtd

for i in 2 4 6 8; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "HGTD::NegativeEndcap_layer_${i}_grid.csv" \
        "HGTD::NegativeEndcap_layer_${i}_surface_center.csv" \
        -o "HGTD_NegativeEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "HGTD::PositiveEndcap_layer_${i}_grid.csv" \
        "HGTD::PositiveEndcap_layer_${i}_surface_center.csv" \
        -o "HGTD_PositiveEndcap_layer_${i}_surface_grid.pdf"
done
