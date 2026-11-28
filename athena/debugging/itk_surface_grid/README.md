# ITk surface grid

Local grid bins vs surface centres of the ACTS ITk surface arrays, one PDF per
layer. The CSVs (`<layer>_grid.csv`, `<layer>_surface_center.csv`) are written
by the Athena debug branch `tmp-acts-investigate-surface-grid` during a
one-event reco:

```bash
cd ~/cern/data/itk_surface_grid/<run> && Reco_tf.py --inputRDOFile <ttbar RDO> --outputAODFile AOD.acts.root --maxEvents 1
~/cern/scripts/athena/debugging/itk_surface_grid/plot_surface_grid.sh ~/cern/data/itk_surface_grid/<run>   # JOBS=4
```

`plot_surface_grid.py <grid.csv> <surface_center.csv> -o out.pdf` plots one layer.
