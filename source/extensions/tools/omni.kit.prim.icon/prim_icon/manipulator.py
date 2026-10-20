# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["IconManipulator", "PreventOthers"]

import asyncio
import functools

import carb.settings
import omni.kit.app
import omni.kit.viewport.utility as vpUtil
import omni.ui as ui
from omni.ui import color as cl
from omni.ui import scene as sc
from pxr import Gf

SHOW_TITLE_PATH = "exts/omni.kit.prim.icon/showTitle"


class PreventOthers(sc.GestureManager):
    """
    Don't Hide any other gestures, just make itself can't be prevented
    """

    def __init__(self):
        super().__init__()

    def can_be_prevented(self, gesture):
        return False

    def should_prevent(self, gesture, preventer):
        if preventer.state == sc.GestureState.BEGAN or preventer.state == sc.GestureState.CHANGED:
            return True
        return super().should_prevent(gesture, preventer)


class IconManipulator(sc.Manipulator):
    def __init__(self, icon_scale: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self._icons = {}
        self._icons_images = {}
        self._icon_panel = None
        self._icon_scale = icon_scale

    def on_build(self):
        if not self.model:
            return
        self._icon_panel = sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 0, 0))
        self.rebuild_icons()

    def rebuild_icons(self, need_check=False):
        self._icons = {}
        self._icons_images = {}
        for prim_path in self._icons.keys():
            self._icons[prim_path].clear()
        self._icon_panel.clear()
        with self._icon_panel:
            for prim_path in self.model.get_prim_paths():
                self.build_icon_by_path(prim_path, need_check)

    # check the position in world is in viewport 2d screen space
    def check_viewport_pos(self, position):
        viewport_api = vpUtil.get_active_viewport()
        if not viewport_api:
            return False
        world_to_ndc = viewport_api.world_to_ndc
        ndc_pos = world_to_ndc.Transform(position)

        # this interface will return none viewport if pos outside the viewport area
        pos, viewport = viewport_api.map_ndc_to_texture([ndc_pos[0], ndc_pos[1]])
        return viewport is not None

    def build_icon_by_path(self, prim_path, need_check):
        icon_pos = self.model.get_position(prim_path)
        if not icon_pos:
            return
        if need_check:
            if not self.check_viewport_pos(icon_pos):
                return
        icon_trans = sc.Transform(
            look_at=sc.Transform.LookAt.CAMERA,
            transform=sc.Matrix44.get_translation_matrix(*icon_pos),
        )
        icon_url = self.model.get_icon_url(prim_path)
        prevent_others = PreventOthers()

        # markup tool's color has different color
        self._icons[prim_path] = icon_trans
        with icon_trans:
            with sc.Transform(scale_to=sc.Space.NDC):
                # sc.Space.NDC - Normalizes the scale, so we're basically talking what % size of the screen
                click_gesture = sc.ClickGesture(
                    name="primicon_click",
                    on_ended_fn=lambda sender: self._on_clicked(sender),
                )
                icons_image = sc.Image(
                    icon_url,
                    0.09 * self._icon_scale,
                    0.09 * self._icon_scale,
                    # the prevent_others manager is to make this click gesture couldn't be hide
                    gesture=sc.ClickGesture(functools.partial(self._icon_clicked, prim_path), manager=prevent_others),
                )
                self._icons_images[prim_path] = icons_image
            show_title = carb.settings.get_settings().get(SHOW_TITLE_PATH)
            if show_title:
                with sc.Transform(scale_to=sc.Space.NDC, transform=sc.Matrix44.get_translation_matrix(-0.03, -0.04, 0)):
                    name = prim_path.split("/")[-1]
                    if len(name) > 12:
                        name = name[0:4] + "..." + name[-4:]
                    sc.Label(name)

    def on_model_updated(self, item):
        if not item:
            # That trigger by model clear
            self.invalidate()
            return
        prim_path = item.prim_path
        if prim_path in self._icons:
            if item.removed:
                self._icons[prim_path].clear()
                self._icons[prim_path] = None
                self._icons.pop(prim_path)
                if prim_path in self._icons_images:
                    self._icons_images.pop(prim_path)
            else:
                if item.visible:
                    self._icons[prim_path].visible = True
                else:
                    self._icons[prim_path].visible = False
        else:
            if not self._icon_panel:
                self._icon_panel = sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 0, 0))
            with self._icon_panel:
                self.build_icon_by_path(prim_path, False)

    def _icon_clicked(self, prim_path, shape: sc.AbstractShape):
        if prim_path in self._icons:

            async def delay_click():
                await omni.kit.app.get_app().next_update_async()
                self.model.get_on_click(prim_path)(prim_path)

            asyncio.ensure_future(delay_click())
