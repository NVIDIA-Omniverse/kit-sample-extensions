import copy
import os
import weakref
from functools import partial
from pathlib import Path
from typing import List, Set

import carb
import omni.ui as ui
import omni.usd
from omni.kit.async_engine import run_coroutine
from omni.kit.material.library.search_widget import SearchWidget
from omni.kit.property.material.scripts.material_utils import (
    Constant,
    get_binding_from_prims,
)
from omni.kit.property.material.scripts.usd_binding_widget import (
    UsdBindingAttributeWidget,
)
from omni.kit.property.usd.prim_selection_payload import PrimSelectionPayload
from omni.kit.window.property.templates import LABEL_HEIGHT, LABEL_WIDTH
from pxr import Sdf, Usd, UsdShade

from . import ui_const as ui_c
from .core import VariantEditorCore
from .property_watcher import PropertyWatchButton

EXT_PATH = Path(__file__).parent.parent.parent.parent.parent


class UsdVariantBindingAttributeWidget(UsdBindingAttributeWidget):
    def __init__(
        self,
        extension_path,
        stage,
        attr_name,
        metadata,
        prim_paths,
        add_context_menu=False,
        can_edit=True,
    ):
        super().__init__(
            extension_path,
            add_context_menu,
            collapsable=False,
            enable_bound_widget=False,
        )
        self._stage = weakref.ref(stage)
        self._payload = PrimSelectionPayload(self._stage, prim_paths)
        self._attr_name = attr_name
        self._metadata = metadata
        self._core = VariantEditorCore.get_instance()
        self._can_edit = can_edit

    def _build_material_popup(
        self,
        material_list: List[str],
        material_index: int,
        thumbnail_image: ui.Button,
        bound_prim_list: Set[Usd.Prim],
        material_missing: bool,
        bind_material_fn: callable,
        on_goto_fn: callable,
        on_dragdrop_fn: callable,
    ):
        def drop_accept(url):
            if not self._can_edit:
                return False

            if len(url.split("\n")) > 1:
                carb.log_warn("build_material_popup multi-file drag/drop not supported")
                return False

            if url.startswith("material::"):
                return True

            url_ext = os.path.splitext(url)[1]
            return url_ext.lower() in [".mdl"]

        def dropped_mtl(event, bind_material_fn):
            url = event.mime_data
            subid = None
            # remove omni.kit.browser.material "material::" prefix
            if url.startswith("material::"):
                url = url[10:]
                parts = url.split(".mdl@")
                if len(parts) == 2:
                    subid = parts[1]
                    url = url.replace(f".mdl@{subid}", ".mdl")

            bind_material_fn(url=url, subid=subid)

        name_field, listbox_button, goto_button = self._search_widget.build_ui_popup(
            search_size=LABEL_HEIGHT,
            popup_text=(material_list[material_index] if material_index >= 0 else "Mixed"),
            index=material_index,
            update_fn=bind_material_fn,
            widget_flags=(
                SearchWidget.WidgetFlags.SHOW_ALL if self._can_edit else SearchWidget.WidgetFlags.SHOW_GOTO_BUTTON
            ),
            missing=material_missing,
        )
        if self._can_edit:
            name_field.set_mouse_pressed_fn(
                lambda x, y, b, m, f=name_field: self._show_material_popup(f, material_index, bind_material_fn)
            )
            name_field.set_accept_drop_fn(drop_accept)
            name_field.set_drop_fn(partial(dropped_mtl, bind_material_fn=on_dragdrop_fn))

            listbox_button.set_mouse_pressed_fn(
                lambda x, y, b, m, f=name_field: self._show_material_popup(f, material_index, bind_material_fn)
            )

            if material_index > 0 and goto_button:
                goto_button.set_mouse_pressed_fn(lambda x, y, b, m, f=name_field: on_goto_fn(f.model))

            thumbnail_image.set_accept_drop_fn(drop_accept)
            thumbnail_image.set_drop_fn(partial(dropped_mtl, bind_material_fn=on_dragdrop_fn))

    def _build_combo(self, material_list: List[str], material_index: int, on_fn: callable):
        def set_visible(widget, visible):
            widget.visible = visible

        with ui.ZStack():
            combo = ui.ComboBox(material_index, *material_list)
            if self._can_edit:
                combo.model.add_item_changed_fn(on_fn)
            if material_index == -1:
                placeholder = ui.Label(
                    "Mixed",
                    height=LABEL_HEIGHT,
                    name="combo_mixed",
                )
                self._combo_subscription.append(
                    combo.model.get_item_value_model().subscribe_value_changed_fn(
                        lambda m, w=placeholder: set_visible(w, m.as_int < 0)
                    )
                )
            return combo

    def get_active_variant_set(self):
        vset_name = self._core._get_active_variant_set()
        vset = self._core._get_variant_set_by_name(vset_name)
        return vset_name, vset

    def send_edit_variant_command(self, cmd_name, **kargs):
        vset_name, vset = self.get_active_variant_set()
        with VariantEditorCore.get_instance().AuthorVariant():
            omni.kit.commands.execute(
                "EditVariant",
                prim_path=vset.GetPrim().GetPath().pathString,
                variant_set_name=vset_name,
                cmd_name=cmd_name,
                cmd_args={**kargs},
            )

    def bind_material_to_prims(self, bind_material_path, items):
        if self._can_edit:
            prim_path_list = []
            strength_list = []
            for prim_path, material_name, strength in items:
                if str(material_name) != str(bind_material_path):
                    prim_path_list.append(prim_path)
                    strength_list.append(strength)

            if str(bind_material_path) == Constant.SDF_PATH_INVALID:
                bind_material_path = None

            self.send_edit_variant_command(
                "BindMaterial",
                material_path=bind_material_path,
                prim_path=prim_path_list,
                strength=strength_list,
            )

    def get_on_strength_changed_callback(self):
        def on_strength_changed(model, item, relationships):
            index = model.get_item_value_model().as_int
            if index < 0 or index >= len(self._strengths):
                carb.log_error(f"on_strength_changed with invalid index {index}")
                return
            bind_strength = list(self._strengths.values())[index]
            for relationship in relationships:
                self.send_edit_variant_command("SetMaterialStrength", rel=relationship, strength=bind_strength)

        return on_strength_changed

    def build_thumbnail_widget(self, style_name, material_path, index):
        OVERRIDE_ICON_SIZE = 50
        with ui.ZStack(width=0):
            image_button = ui.Button(
                "",
                width=OVERRIDE_ICON_SIZE,
                height=OVERRIDE_ICON_SIZE,
                fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT,
                name=style_name,
                identifier="preview_drop_target",
            )

            if index != -1:
                material_prim = self._get_prim(material_path)
                if material_prim:

                    def on_image_progress(button: ui.Button, image: ui.Image, progress: float):
                        if progress > 0.999:
                            button.image_url = image.source_url
                            image.visible = False

                    thumbnail_image = ui.Image(
                        width=OVERRIDE_ICON_SIZE,
                        height=OVERRIDE_ICON_SIZE,
                        fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT,
                        name="material",
                    )
                    self._thumbnail_loader.load(material_prim, thumbnail_image)
                    # callback when image is loading
                    thumbnail_image.set_progress_changed_fn(
                        lambda p, b=image_button, i=thumbnail_image: on_image_progress(b, i, p)
                    )
            return image_button

    def _build_binding_info(
        self,
        inherited: bool,
        style_name: str,
        material_list: List[str],
        material_path: str,
        strength_value: str,
        bound_prim_list: Set[str],
        material_missing: bool,
        on_material_fn: callable,
        on_strength_fn: callable,
        on_goto_fn: callable,
        on_dragdrop_fn: callable,
    ):
        material_list = copy.copy(material_list)
        if material_list[0] == Constant.SDF_PATH_INVALID:
            material_list[0] = "None"
        if material_path == Constant.SDF_PATH_INVALID:
            material_path = "None"

        prim_style, type_label, bound_prims = self._get_type_label_and_bounded_prims(bound_prim_list)

        if not self._first_row:
            ui.Separator(height=10, menu_compatibility=False)
        self._first_row = False

        index = self._get_index(material_list, material_path, -1)

        ui.Spacer(width=6)
        with ui.HStack(style=self._style):
            ui.Label("Material", width=ui_c.PROPERTY_LABEL_WIDTH)

            with ui.VStack(spacing=0, width=ui_c.PROPERTY_LABEL_HEIGHT + 1):
                property_path = bound_prim_list[-1].GetPath().AppendProperty("material:binding")
                self._property_watcher = PropertyWatchButton(
                    property_path,
                )

            ui.Spacer(width=6)
            image_button = self.build_thumbnail_widget(style_name, material_path, index)
            ui.Spacer(width=6)

            with ui.VStack(spacing=5):
                if self._enable_bound_widget and self._filter.matches(type_label):
                    self._any_item_visible = True
                    self.build_bound_widget(type_label, prim_style, bound_prims)

                if index != -1 and inherited:
                    inherited_list = copy.copy(material_list)
                    inherited_list[index] = f"{inherited_list[index]} (inherited)"
                    self._build_material_popup(
                        inherited_list,
                        index,
                        image_button,
                        bound_prim_list,
                        material_missing,
                        on_material_fn,
                        on_goto_fn,
                        on_dragdrop_fn,
                    )
                else:
                    self._build_material_popup(
                        material_list,
                        index,
                        image_button,
                        bound_prim_list,
                        material_missing,
                        on_material_fn,
                        on_goto_fn,
                        on_dragdrop_fn,
                    )

                if self._enable_strength_widget and self._filter.matches("Strength"):
                    self._any_item_visible = True
                    self.build_strength_widget(strength_value, on_strength_fn)


class VariantMaterialBindingWidgetBuilder:

    @classmethod
    def build_material_binding(cls, stage, attr_name, metadata, prim_paths: List[Sdf.Path], can_edit):
        binding_widget = UsdVariantBindingAttributeWidget(
            EXT_PATH, stage, attr_name, metadata, prim_paths, False, can_edit
        )
        binding_widget.build()
