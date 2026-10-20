# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
from pathlib import Path

import carb
import omni.kit.app
import omni.ui as ui
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf

from ..material_preview_producer import MaterialPreviewProducer
from ..simple_viewport_widget import SimpleViewportWidget

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))


class TestPreview(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = EXTENSION_FOLDER_PATH.absolute().resolve().joinpath("data/tests")

    # After running each test
    async def tearDown(self):
        self._golden_img_dir = None
        await super().tearDown()

    async def test_general(self):
        """Testing general properties of MaterialPreviewProducer"""
        window = await self.create_test_window()

        test_file_path = self._golden_img_dir.joinpath("material.usda").absolute()
        usd_context = omni.usd.get_context()
        await usd_context.open_stage_async(f"{test_file_path}")
        await omni.kit.app.get_app().next_update_async()

        hydra_engine_name = carb.settings.get_settings().get("/renderer/active") or "pxr"
        material_preview_producer = MaterialPreviewProducer(hydra_engine_name=hydra_engine_name)

        material_preview_producer.set_material(Sdf.Path("/World/Looks/PreviewSurface"))
        material_preview_producer.resolution = [512, 512]

        viewport_provider = ui.ImageProvider()
        drawn = asyncio.Event()

        def __on_drawable_changed():
            """Called by material_preview_producer when the resolution is changed"""
            gpu_reference = material_preview_producer.gpu_reference
            if gpu_reference:
                viewport_provider.set_image_data(gpu_reference)
                drawn.set()

        viewport_provider = ui.ImageProvider()
        drawable_change_sub = material_preview_producer.set_on_drawable_changed_fn(__on_drawable_changed)

        with window.frame:
            # The viewport
            viewport_image = ui.ImageWithProvider(
                viewport_provider,
                alignment=ui.Alignment.CENTER,
                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
            )

        try:
            await drawn.wait()

            self.assertEqual(viewport_provider.width, 512)
            self.assertEqual(viewport_provider.height, 512)

            # test set_captured_data and get_captured_raw_data
            await material_preview_producer.set_captured_data_async()

            await omni.kit.app.get_app().next_update_async()

            data = material_preview_producer.get_captured_raw_data()
            self.assertIsNotNone(data)
            self.assertEqual(len(data[0]), 512 * 512 * 4)
            self.assertEqual(data[1], 512)
            self.assertEqual(data[2], 512)

        except asyncio.TimeoutError:
            carb.log_warn("Timed out waiting for previewing the material!")

        await self.finalize_test_no_image()
        material_preview_producer.destroy()

    async def test_simple_viewport_widget(self):
        """Testing SimpleViewportWidget"""
        window = await self.create_test_window()
        await omni.usd.get_context().new_stage_async()
        context_name = omni.usd.get_context().get_name()

        with window.frame:
            widget = SimpleViewportWidget(context_name, "dummy")
            widget._hydra_texture.width = 512
            await omni.usd.get_context().new_stage_async()

            widget.destroy()

        await self.finalize_test_no_image()
