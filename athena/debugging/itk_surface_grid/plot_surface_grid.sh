#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# pixel

for i in 2 4; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelInner_Barrel_layer_${i}_grid.csv" \
        "ITkPixelInner_Barrel_layer_${i}_surface_center.csv" \
        -o "ITkPixelInner_Barrel_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36 38 40 42 44 46 48 50 52 54 56 58; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelInner_NegativeEndcap_layer_${i}_grid.csv" \
        "ITkPixelInner_NegativeEndcap_layer_${i}_surface_center.csv" \
        -o "ITkPixelInner_NegativeEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36 38 40 42 44 46 48 50 52 54 56 58; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelInner_PositiveEndcap_layer_${i}_grid.csv" \
        "ITkPixelInner_PositiveEndcap_layer_${i}_surface_center.csv" \
        -o "ITkPixelInner_PositiveEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter_Barrel_layer_${i}_grid.csv" \
        "ITkPixelOuter_Barrel_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_Barrel_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter_NegativeEndcap_Ring0_layer_${i}_grid.csv" \
        "ITkPixelOuter_NegativeEndcap_Ring0_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_NegativeEndcap_Ring0_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter_PositiveEndcap_Ring0_layer_${i}_grid.csv" \
        "ITkPixelOuter_PositiveEndcap_Ring0_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_PositiveEndcap_Ring0_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter_NegativeEndcap_Ring1_layer_${i}_grid.csv" \
        "ITkPixelOuter_NegativeEndcap_Ring1_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_NegativeEndcap_Ring1_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter_PositiveEndcap_Ring1_layer_${i}_grid.csv" \
        "ITkPixelOuter_PositiveEndcap_Ring1_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_PositiveEndcap_Ring1_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter_NegativeEndcap_Ring2_layer_${i}_grid.csv" \
        "ITkPixelOuter_NegativeEndcap_Ring2_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_NegativeEndcap_Ring2_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkPixelOuter_PositiveEndcap_Ring2_layer_${i}_grid.csv" \
        "ITkPixelOuter_PositiveEndcap_Ring2_layer_${i}_surface_center.csv" \
        -o "ITkPixelOuter_PositiveEndcap_Ring2_layer_${i}_surface_grid.pdf"
done

# strips

for i in 2 4 6 8; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkStrip_Barrel_layer_${i}_grid.csv" \
        "ITkStrip_Barrel_layer_${i}_surface_center.csv" \
        -o "ITkStrip_Barrel_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkStrip_NegativeEndcap_layer_${i}_grid.csv" \
        "ITkStrip_NegativeEndcap_layer_${i}_surface_center.csv" \
        -o "ITkStrip_NegativeEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8 10 12; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "ITkStrip_PositiveEndcap_layer_${i}_grid.csv" \
        "ITkStrip_PositiveEndcap_layer_${i}_surface_center.csv" \
        -o "ITkStrip_PositiveEndcap_layer_${i}_surface_grid.pdf"
done

# hgtd

for i in 2 4 6 8; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "HGTD_NegativeEndcap_layer_${i}_grid.csv" \
        "HGTD_NegativeEndcap_layer_${i}_surface_center.csv" \
        -o "HGTD_NegativeEndcap_layer_${i}_surface_grid.pdf"
done

for i in 2 4 6 8; do
    python "${SCRIPT_DIR}/plot_surface_grid.py" \
        "HGTD_PositiveEndcap_layer_${i}_grid.csv" \
        "HGTD_PositiveEndcap_layer_${i}_surface_center.csv" \
        -o "HGTD_PositiveEndcap_layer_${i}_surface_grid.pdf"
done
