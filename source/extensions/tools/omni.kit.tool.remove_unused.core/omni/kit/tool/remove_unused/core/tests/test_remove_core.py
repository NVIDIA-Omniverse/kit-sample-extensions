# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import pathlib

import omni.kit.app
import omni.kit.test
from pxr import Usd

from ..core import RemoveUnusedCore as core

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
DATA_DIR = EXTENSION_FOLDER_PATH.joinpath("data")

expected_materials = {
    "/World/Looks/Clear_Glass",
    "/World/Looks/Carpet_Charcoal",
    "/World/Looks/Carpet_Diamond_Yellow_01",
    "/World/Looks/Brick_Pavers",
    "/World/Looks/CorrugatedMetal",
    "/World/Looks/Carpet_Diamond_Yellow",
    "/World/Looks/Chrome",
    "/World/Looks/Carpet_Forest",
    "/World/Looks/Ash_Planks",
    "/World/Looks/Brushed_Antique_Copper",
    "/World/Looks/Bamboo_Planks",
    "/World/Looks/Cherry",
    "/World/Looks/Brushed_Antique_Copper_01",
    "/World/Looks/Aluminum_Anodized",
    "/World/Looks/Carpet_Berber_Gray",
    "/World/Looks/Carpet_Diamond_Olive",
}


class TestRemoveCoreCommand(omni.kit.test.AsyncTestCase):
    # inherits from async test case
    def setUp(self):
        self._test_stage = self._open_stage("mat_removal_test")

    # inherits from async test case
    def tearDown(self):
        self._test_stage = None

    # Test the "Remove Materials" Functionality on a prepared stage with assigned and unassigned materials.
    # Some materials are assigned in a sublayer, these should not be removed.
    async def test_collect_mats(self):

        expected_matlist = set()
        matlist = set()

        matlist.update(core.get_excess_materials(self._test_stage))
        expected_matlist.update(expected_materials)

        message = "Material list does not contain expected unused materials."

        self.assertEqual(matlist, expected_matlist, message)

    # ============= UTILITY ===============

    def _open_stage(self, stage_name: str, usd_context_name: str = ""):
        usd_context = omni.usd.get_context(usd_context_name)
        path = DATA_DIR.joinpath(stage_name + ".usda")
        usd_context.open_stage(str(path))
        stage = usd_context.get_stage()
        return stage
