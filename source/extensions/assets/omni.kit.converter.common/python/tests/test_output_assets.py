# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import shutil
from pathlib import Path
from unittest.mock import patch

import omni.kit.test
from pxr import Usd


class TestOutputAssetTransfer(omni.kit.test.AsyncTestCase):
    async def test_transfer_textures_and_layers(self):
        import tempfile
        from unittest.mock import AsyncMock

        from omni.kit.converter.common import OmniClientWrapper, copy_output_assets
        from pxr import Sdf

        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source"
            source.mkdir()
            textures = source / "Textures"
            textures.mkdir()
            (textures / "color.png").write_bytes(b"test image")
            child = Usd.Stage.CreateNew(str(source / "child.usda"))
            prim = child.DefinePrim("/Material")
            prim.CreateAttribute("image", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("Textures/color.png"))
            child.GetRootLayer().Save()
            # JT partitions can live outside the root layer's directory.
            (source / "output").mkdir()
            stage = Usd.Stage.CreateNew(str(source / "output/model.usda"))
            stage.GetRootLayer().subLayerPaths = ["../child.usda"]
            stage.GetRootLayer().Save()
            remote = root / "remote"
            remote.mkdir()
            old_texture = remote / "Textures" / "color.png"
            old_texture.parent.mkdir()
            old_texture.write_bytes(b"existing image")
            copied = []

            async def copy(src, dest):
                relative = dest.removeprefix("omniverse://server/output/")
                target = remote / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, target)
                copied.append(relative)
                return True

            with (
                patch.object(OmniClientWrapper, "copy", side_effect=copy),
                patch.object(OmniClientWrapper, "create_folder", new=AsyncMock(return_value=True)),
            ):
                await copy_output_assets(str(source / "output/model.usda"), "omniverse://server/output/model.usda")
            self.assertEqual(copied[-1], "model.usda")
            self.assertEqual(len(copied), 3)
            self.assertEqual(old_texture.read_bytes(), b"existing image")
            result = Usd.Stage.Open(str(remote / "model.usda"))
            image = result.GetPrimAtPath("/Material").GetAttribute("image").Get()
            self.assertTrue(image.resolvedPath)
            self.assertTrue(Path(image.resolvedPath).is_relative_to(remote))
            self.assertEqual(Path(image.resolvedPath).read_bytes(), b"test image")
            result = stage = child = None

    async def test_failed_asset_copy_does_not_publish_root(self):
        import tempfile
        from unittest.mock import AsyncMock

        from omni.kit.converter.common import OmniClientWrapper, copy_output_assets
        from pxr import Sdf

        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "image.png").write_bytes(b"test image")
            stage = Usd.Stage.CreateNew(str(root / "model.usda"))
            stage.DefinePrim("/Material").CreateAttribute("image", Sdf.ValueTypeNames.Asset).Set(
                Sdf.AssetPath("image.png")
            )
            stage.GetRootLayer().Save()
            with (
                patch.object(OmniClientWrapper, "copy", new=AsyncMock(return_value=False)) as copy,
                patch.object(OmniClientWrapper, "create_folder", new=AsyncMock(return_value=True)),
            ):
                with self.assertRaisesRegex(OSError, "Could not copy converted asset"):
                    await copy_output_assets(str(root / "model.usda"), "omniverse://server/output/model.usda")
                self.assertEqual(copy.await_count, 1)
                self.assertTrue(copy.call_args.args[0].endswith("image.png"))
            stage = None
