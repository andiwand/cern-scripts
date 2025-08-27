#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

generate_commands() {
    for i in 2 4; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelInner::Barrel_layer_${i}_grid.csv\" \
            \"ITkPixelInner::Barrel_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelInner_Barrel_layer_${i}_surface_grid.pdf\""
    done

    for i in {2..58..2}; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelInner::NegativeEndcap_layer_${i}_grid.csv\" \
            \"ITkPixelInner::NegativeEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelInner_NegativeEndcap_layer_${i}_surface_grid.pdf\""

        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelInner::PositiveEndcap_layer_${i}_grid.csv\" \
            \"ITkPixelInner::PositiveEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelInner_PositiveEndcap_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelOuter::Barrel_layer_${i}_grid.csv\" \
            \"ITkPixelOuter::Barrel_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelOuter_Barrel_layer_${i}_surface_grid.pdf\""
    done

    for i in {2..34..2}; do
        for ring in Ring0 Ring1 Ring2; do
            if [[ "$ring" == "Ring2" && "$i" -gt 36 ]]; then continue; fi
            echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
                \"ITkPixelOuter::NegativeEndcap::${ring}_layer_${i}_grid.csv\" \
                \"ITkPixelOuter::NegativeEndcap::${ring}_layer_${i}_surface_center.csv\" \
                -o \"ITkPixelOuter_NegativeEndcap_${ring}_layer_${i}_surface_grid.pdf\""

            echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
                \"ITkPixelOuter::PositiveEndcap::${ring}_layer_${i}_grid.csv\" \
                \"ITkPixelOuter::PositiveEndcap::${ring}_layer_${i}_surface_center.csv\" \
                -o \"ITkPixelOuter_PositiveEndcap_${ring}_layer_${i}_surface_grid.pdf\""
        done
    done

    for i in 2 4 6 8; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkStrip::Barrel_layer_${i}_grid.csv\" \
            \"ITkStrip::Barrel_layer_${i}_surface_center.csv\" \
            -o \"ITkStrip_Barrel_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6 8 10 12; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkStrip::NegativeEndcap_layer_${i}_grid.csv\" \
            \"ITkStrip::NegativeEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkStrip_NegativeEndcap_layer_${i}_surface_grid.pdf\""

        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkStrip::PositiveEndcap_layer_${i}_grid.csv\" \
            \"ITkStrip::PositiveEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkStrip_PositiveEndcap_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6 8; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"HGTD::NegativeEndcap_layer_${i}_grid.csv\" \
            \"HGTD::NegativeEndcap_layer_${i}_surface_center.csv\" \
            -o \"HGTD_NegativeEndcap_layer_${i}_surface_grid.pdf\""

        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"HGTD::PositiveEndcap_layer_${i}_grid.csv\" \
            \"HGTD::PositiveEndcap_layer_${i}_surface_center.csv\" \
            -o \"HGTD_PositiveEndcap_layer_${i}_surface_grid.pdf\""
    done
}

# Export the function so it's available to parallel
export -f generate_commands

# Generate commands and run them in parallel
generate_commands | parallel -j "$(nproc)"
