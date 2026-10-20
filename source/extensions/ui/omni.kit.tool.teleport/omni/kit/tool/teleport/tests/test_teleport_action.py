# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# import omni.kit.ui_test as ui_test
# from .utils import TestTeleportBase
# import carb.settings

# SETTING_SHOW_POSITION = "exts/omni.kit.tool.teleport/showPosition"


# class TestNavigationAction(TestTeleportBase):
#     async def setUp(self):
#         await super().setUp()
#         # await ui_test.human_delay(8)
#         # await ui_test.wait_n_updates(300)

#     async def test_navigation_teleport_drag_and_drop(self):
#         """Test navigation teleport buttons."""
#         await self._dock_viewport()
#         self._teleport.set_active(True, test=True)
#         await ui_test.wait_n_updates(3)
#         self._teleport.unbind_widget_material()
#         await ui_test.human_delay(8)
#         await ui_test.wait_n_updates(30)
#         # await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(600, 480), ui_test.Vec2(600, 490))
#         await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(500, 500), ui_test.Vec2(540, 540))
#         await ui_test.human_delay(8)
#         await ui_test.wait_n_updates(30)
#         await self.finalize_test(threshold=11.5, golden_img_dir=self._golden_img_dir, golden_img_name="teleport_drag.png")

#     async def test_navigation_teleport_move(self):
#         """Test navigation teleport buttons."""
#         await self._dock_viewport()
#         self._teleport.set_active(True, test=True)
#         self._teleport.unbind_widget_material()
#         await ui_test.human_delay(8)
#         await ui_test.wait_n_updates(30)
#         # await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(600, 480), ui_test.Vec2(600, 490))
#         await ui_test.emulate_mouse_move(ui_test.Vec2(500, 510))
#         await ui_test.human_delay(8)
#         await ui_test.wait_n_updates(30)
#         await self.finalize_test(threshold=11.5, golden_img_dir=self._golden_img_dir, golden_img_name="teleport_move.png")

#     async def test_navigation_teleport_show_position(self):
#         """Test navigation teleport buttons."""
#         await self._dock_viewport()
#         self._teleport.set_active(True, test=True)
#         self._teleport.unbind_widget_material()
#         await ui_test.human_delay(8)
#         carb.settings.get_settings().set(SETTING_SHOW_POSITION, True)
#         await ui_test.wait_n_updates(30)
#         # await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(600, 480), ui_test.Vec2(600, 490))
#         await ui_test.emulate_mouse_move(ui_test.Vec2(600, 450))
#         await ui_test.human_delay(8)
#         await ui_test.wait_n_updates(30)
#         await self.finalize_test(threshold=11.5, golden_img_dir=self._golden_img_dir, golden_img_name="teleport_positon.png")
