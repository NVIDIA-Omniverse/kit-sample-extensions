# 3D Gaussian Splat Converter [omni.kit.converter.gsplat]

Converts 3D Gaussian Splat (`.ply` / `.spz`) data to USD using the
`ParticleField3DGaussianSplat` schema.

## Features

- **PLY reader** -- supports binary (little/big endian) and ASCII PLY files
  with standard 3DGS vertex properties (positions, scales, rotations, opacity,
  spherical harmonics).
- **SPZ reader** -- supports Niantic SPZ v2 and v3 compressed Gaussian Splat
  files.
- **USD writer** -- produces `.usd`, `.usda`, `.usdc`, or `.usdz` files using
  `UsdVol.ParticleField3DGaussianSplat` (OpenUSD 26.03+) or the Omniverse
  `omni.usd.schema.usd_particle_field` backport.
- **PLY writer** -- re-exports decoded splat data as standard float32 PLY.
- **CLI** -- conversion via `python -m usd_convert_gsplat` (pip) or the Kit shims
  `python -m omni.kit.converter.gsplat` / `python -m omni.kit.converter.gsplat.cli`.

## Usage

### Sample Inputs

Use public sample data when you need a quick file to test conversion:

- **PLY** -- Steam Studio provides CC0 3D Gaussian Splat PLY samples at
  <https://note.com/steam_studio/n/ne9736d94f162>.
- **SPZ** -- Niantic publishes SPZ sample assets in the `spz` repository at
  <https://github.com/nianticlabs/spz/tree/main>.

### Kit Extension (Asset Importer)

Enable `omni.kit.converter.gsplat` in the Extension Manager. There is **no** standalone Tools window; splat conversion in Kit is through **omni.kit.tool.asset_importer**.

Use **File → Import** or **Convert to USD**: for `.ply` you can choose **Asset Importer** (default, mesh) or **3D Gaussian Splat (Particle Field)**; `.spz` uses the splat path only.

### CLI

```bash
# From a pip install (recommended for scripts):
python -m usd_convert_gsplat -i input.ply -o output.usda

# From Kit / extension layout (shims delegate to usd_convert_gsplat):
python -m omni.kit.converter.gsplat.cli -i input.spz -o output.usdz
```

### Python API

Core types and functions live in **`usd_convert_gsplat`**. Inside Kit,
`omni.kit.converter.gsplat` re-exports the same symbols for convenience.

```python
from usd_convert_gsplat import read_ply, read_spz, write_gaussian_splat_usd

splat_data = read_ply("scene.ply")
write_gaussian_splat_usd(splat_data, "scene.usdz", source_file="scene.ply")
```

## Dependencies

- `omni.usd`
- `omni.ui`
- `omni.usd.schema.usd_particle_field`
- `numpy` (bundled with Kit via `omni.kit.pip_archive` dependency)
