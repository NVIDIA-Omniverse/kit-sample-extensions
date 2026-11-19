# License Map

Unless listed below, the contents of this repository are NVIDIA proprietary software licensed
under the NVIDIA Software License Agreement in [LICENSE](LICENSE).

The directories and files below are licensed differently. Where a file carries an
`SPDX-License-Identifier` header, that header states the license for that file. Third-party code
and the packages downloaded by the build are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Standard license texts are in [LICENSES/](LICENSES/).

## Directories

| Path | License | License file |
|---|---|---|
| `source/extensions/warp/omni.warp.core/warp/` | Apache-2.0 (NVIDIA Warp; includes third-party code listed in THIRD_PARTY_NOTICES.md) | [`LICENSE.md`](source/extensions/warp/omni.warp.core/warp/LICENSE.md) |
| `source/extensions/assets/omni.asset_validator.core/` | Apache-2.0 | [`PACKAGE-LICENSES/omni.asset_validator.core-LICENSE.md`](source/extensions/assets/omni.asset_validator.core/PACKAGE-LICENSES/omni.asset_validator.core-LICENSE.md) |
| `source/extensions/assets/omni.asset_validator.ui/` | Apache-2.0 | [`PACKAGE-LICENSES/omni.asset_validator.ui-LICENSE.md`](source/extensions/assets/omni.asset_validator.ui/PACKAGE-LICENSES/omni.asset_validator.ui-LICENSE.md) |
| `source/extensions/ui/omni.simready.content.browser/` | Apache-2.0 | [`PACKAGE-LICENSES/omni.simready.content.browser-LICENSE.md`](source/extensions/ui/omni.simready.content.browser/PACKAGE-LICENSES/omni.simready.content.browser-LICENSE.md) |

## Individual files

| Path | License |
|---|---|
| `repo.sh`, `repo.bat`, `tools/repoman/repoman_bootstrapper.py` | MIT ([LICENSES/MIT.txt](LICENSES/MIT.txt)) |
| `tools/packman/packman.cmd`, `tools/packman/python.sh`, `tools/packman/python.bat` | Apache-2.0 ([LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt)) |
| `source/extensions/warp/generate_node_metadata.py`, `source/extensions/warp/omni.warp.menu/omni/warp/menu/__init__.py`, `source/extensions/warp/omni.warp.menu/omni/warp/menu/_impl/__init__.py`, `source/extensions/warp/omni.warp.menu/omni/warp/menu/_impl/extension.py` | Apache-2.0 ([LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt)); the other files of `omni.warp.menu` are NVIDIA proprietary |
| HDR environment maps: `source/extensions/ui/omni.kit.widget.material_preview/data/photo_studio_01_4k.hdr`, `source/extensions/ui/omni.kit.widget.material_preview/data/domeLight/photo_studio_01_4k.hdr`, `source/extensions/ui/omni.kit.thumbnails.mdl/data/template/SubUSDs/textures/photo_studio_01_4k.hdr`, `source/extensions/utils/omni.light_rigs/light_rig_data/light_rigs/HDR/partly_cloudy.hdr`, `source/extensions/utils/omni.light_rigs/light_rig_data/light_rigs/subusds/partly_cloudy.hdr`, `source/extensions/utils/omni.light_rigs/light_rig_data/light_rigs/HDR/CarLight_512x256.hdr`, `source/extensions/utils/omni.light_rigs/light_rig_data/light_rigs/subusds/CarLight_512x256.hdr`, `source/extensions/ui/omni.kit.environment.core/data/tests/Skies/Hdr/CarLight_512x256.hdr` | CC0-1.0, public domain dedication ([LICENSES/CC0-1.0.txt](LICENSES/CC0-1.0.txt)) |
