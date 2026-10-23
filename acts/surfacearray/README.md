# SurfaceArray lookup probes

Standalone probes behind
`~/cern/notes/acts/notebook/2026-09-02_surface-array-lookup-gaps.md`.
They link the ACTS build at `~/cern/build/acts/acts/dev3` directly; there is no
CMake project. Build with `./build.sh <file>.cpp` (Core only),
`./buildex.sh <file>.cpp` (adds the generic detector) or
`./buildodd.sh <file>.cpp` (adds DD4hep + ROOT, needs `source activate.sh` for
`ODD_PATH`).

| probe | what it shows |
|---|---|
| `phi.cpp`, `phiscan.cpp` | phi grid rotation sign: module-centre offset vs the detector phi origin |
| `varphi.cpp` | same defect in `createVariableAxis` |
| `miss.cpp`, `miss2.cpp` | toy barrel truth-vs-lookup; `miss2` classifies each miss by (dphi bin, dz bin) |
| `zoff.cpp`, `zoff1.cpp` | cylinder z axis frame mismatch (Gen3 policy / Gen1 `LayerCreator`) |
| `tol.cpp` | admission tolerance equals the module-centre distance exactly |
| `gen1.cpp`, `geo.cpp`, `geo2.cpp` | `GenericDetector` Gen1 / Gen3 truth-vs-lookup per layer and eta |
| `disc.cpp` | endcap disc: miss rate vs R bins and vs `maxNeighborDistance` |
| `odd1.cpp`, `odd2.cpp`, `sweep.cpp` | ODD Gen1; `sweep` writes `sweep.csv` (layer x bin factor x eta) |
