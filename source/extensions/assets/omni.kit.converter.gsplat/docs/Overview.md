# Overview

`omni.kit.converter.gsplat` converts 3D Gaussian Splat files (`.ply` and `.spz`)
to USD using the `ParticleField3DGaussianSplat` prim type.

The extension provides:

1. **Asset Importer** registration for `.ply` / `.spz` Gaussian splat conversion in Kit.
2. A **Python API** (`read_ply`, `read_spz`, `write_gaussian_splat_usd`) for
   programmatic use (re-exported from `usd_convert_gsplat`).
3. A **CLI** for headless batch conversion.
