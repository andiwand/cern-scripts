#!/bin/bash
# Plot every <layer>_grid.csv with its <layer>_surface_center.csv in a directory -> <layer>_surface_grid.pdf, in parallel.
# usage: plot_surface_grid.sh [dir]   default ~/cern/data/itk_surface_grid; env JOBS (default 4)
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "${1:-$HOME/cern/data/itk_surface_grid}" || exit 1
for g in *_grid.csv; do
  l=${g%_grid.csv}
  [ -f "${l}_surface_center.csv" ] && printf '%s\0' "$l"
done | xargs -0 -P "${JOBS:-4}" -I{} python "$SCRIPT_DIR/plot_surface_grid.py" {}_grid.csv {}_surface_center.csv -o {}_surface_grid.pdf
