#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

generate_commands() {
    for i in 2 4; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelInner_Barrel_layer_${i}_grid.csv\" \
            \"ITkPixelInner_Barrel_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelInner_Barrel_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36 38 40 42 44 46 48 50 52 54 56 58; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelInner_NegativeEndcap_layer_${i}_grid.csv\" \
            \"ITkPixelInner_NegativeEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelInner_NegativeEndcap_layer_${i}_surface_grid.pdf\""

        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelInner_PositiveEndcap_layer_${i}_grid.csv\" \
            \"ITkPixelInner_PositiveEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelInner_PositiveEndcap_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkPixelOuter_Barrel_layer_${i}_grid.csv\" \
            \"ITkPixelOuter_Barrel_layer_${i}_surface_center.csv\" \
            -o \"ITkPixelOuter_Barrel_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36; do
        for ring in Ring0 Ring1 Ring2; do
            if [[ "$ring" == "Ring0" && "$i" -gt 34 ]]; then continue; fi
            if [[ "$ring" == "Ring1" && "$i" -gt 32 ]]; then continue; fi
            if [[ "$ring" == "Ring2" && "$i" -gt 36 ]]; then continue; fi

            echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
                \"ITkPixelOuter_NegativeEndcap_${ring}_layer_${i}_grid.csv\" \
                \"ITkPixelOuter_NegativeEndcap_${ring}_layer_${i}_surface_center.csv\" \
                -o \"ITkPixelOuter_NegativeEndcap_${ring}_layer_${i}_surface_grid.pdf\""

            echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
                \"ITkPixelOuter_PositiveEndcap_${ring}_layer_${i}_grid.csv\" \
                \"ITkPixelOuter_PositiveEndcap_${ring}_layer_${i}_surface_center.csv\" \
                -o \"ITkPixelOuter_PositiveEndcap_${ring}_layer_${i}_surface_grid.pdf\""
        done
    done

    for i in 2 4 6 8; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkStrip_Barrel_layer_${i}_grid.csv\" \
            \"ITkStrip_Barrel_layer_${i}_surface_center.csv\" \
            -o \"ITkStrip_Barrel_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6 8 10 12; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkStrip_NegativeEndcap_layer_${i}_grid.csv\" \
            \"ITkStrip_NegativeEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkStrip_NegativeEndcap_layer_${i}_surface_grid.pdf\""

        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"ITkStrip_PositiveEndcap_layer_${i}_grid.csv\" \
            \"ITkStrip_PositiveEndcap_layer_${i}_surface_center.csv\" \
            -o \"ITkStrip_PositiveEndcap_layer_${i}_surface_grid.pdf\""
    done

    for i in 2 4 6 8; do
        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"HGTD_NegativeEndcap_layer_${i}_grid.csv\" \
            \"HGTD_NegativeEndcap_layer_${i}_surface_center.csv\" \
            -o \"HGTD_NegativeEndcap_layer_${i}_surface_grid.pdf\""

        echo "python \"$SCRIPT_DIR/plot_surface_grid.py\" \
            \"HGTD_PositiveEndcap_layer_${i}_grid.csv\" \
            \"HGTD_PositiveEndcap_layer_${i}_surface_center.csv\" \
            -o \"HGTD_PositiveEndcap_layer_${i}_surface_grid.pdf\""
    done
}

# Export the function so it's available to parallel
export -f generate_commands

# Generate commands and run them in parallel
generate_commands | parallel -j4
