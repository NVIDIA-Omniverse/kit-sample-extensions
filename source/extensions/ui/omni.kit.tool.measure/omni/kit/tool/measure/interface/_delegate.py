# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["MeasurePanelDelegate"]

from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from omni import ui

from ..common import MeasureMode, Precision
from ..manager import MeasurementManager, ReferenceManager
from ..system import MeasurePrim, MeasureSubItem
from .style import STYLE_BUTTON_DELETE, STYLE_BUTTON_GO_TO, STYLE_BUTTON_VISIBILITY, get_icon_path


@dataclass
class TreeUIItemCache:
    """
    Class for keeping track of UI items in the TreeView
    """

    visibility_btn: Optional[ui.Button] = None
    go_to_btn: Optional[ui.Button] = None
    type_img: Optional[ui.Image] = None
    name_field: Optional[ui.StringField] = None
    delete_btn: Optional[ui.Button] = None


class MeasurePanelDelegate(ui.AbstractItemDelegate):
    def __init__(self):
        super().__init__()
        self.__ui_cache: OrderedDict[int, TreeUIItemCache] = OrderedDict()

    @property
    def items(self):
        return self.__ui_cache.items()

    @property
    def item_at(self, index: int):
        for pos, item in enumerate(self.__ui_cache):
            if pos == index:
                return item
        return None

    def _on_visibility_clicked(self, button, image, uuid: int):
        button.checked = not button.checked
        image.source_url = get_icon_path("visibility_off") if button.checked else get_icon_path("visibility_on")

        measure_scene = ReferenceManager().measure_scene
        measure_scene.clear_hovered() if button.checked else measure_scene.set_hovered(uuid, True)
        MeasurementManager().set_visibility(uuid, not button.checked)

    def _on_go_to_clicked(self, button, uuid: int):
        MeasurementManager().frame_measurement(uuid)

    def _on_label_click(self, button, field, label, uuid: int):
        if button != 0:
            return

        def _on_end_edit(model, field, label):
            field.visible = False
            label.text = model.as_string

            MeasurementManager().rename(uuid, name=model.as_string)

            self.subscription = None

        field.visible = True
        field.focus_keyboard()
        self.subscription = field.model.subscribe_end_edit_fn(lambda m, f=field, l=label: _on_end_edit(m, f, l))

    def _on_delete_clicked(self, uuid: int):
        ReferenceManager().ui_manage_panel._measurement_view.clear_selection()
        MeasurementManager().delete(uuid)

    # --------------------------
    def build_header(self, column_id: int = 0) -> None:
        # clear the tree cache before rebuilding
        _ids = ["Visible", "Go to", "Name", "Value", "Type", ""]
        _identifiers = ["VisibleLabel", "GotoLabel", "NameLabel", "ValueLabel", "TypeLabel", ""]
        assert len(_ids) == len(_identifiers)
        ui.Label(_ids[column_id], alignment=ui.Alignment.CENTER, identifier=_identifiers[column_id])

    def build_branch(self, model, item, column_id, level, expanded):
        if item is None:
            return

        if level == 2 and 1 > column_id > 2:
            return

        if column_id == 0 and issubclass(item.__class__, MeasurePrim):
            with ui.HStack(spacing=0):
                if len(item.payload.secondary_values) > 0:
                    ui.Spacer(width=ui.Pixel(4))
                    with ui.VStack(width=ui.Pixel(8)):
                        ui.Spacer()
                        ui.Triangle(
                            style={"background_color": 0xCCFFFFFF},
                            height=ui.Pixel(8),
                            alignment=ui.Alignment.RIGHT_CENTER if not expanded else ui.Alignment.CENTER_BOTTOM,
                        )
                        ui.Spacer()
                else:
                    ui.Spacer(width=ui.Pixel(12))

    def build_widget(self, model, item, column_id, level, expanded):
        if item is None:
            return

        if level == 1 and issubclass(item.__class__, MeasurePrim):
            if self.__ui_cache.get(item.payload.uuid, None) == None:
                self.__ui_cache[item.payload.uuid] = TreeUIItemCache()

            if column_id == 0:  # Visibility
                is_visible = item.payload.visible
                with ui.ZStack(width=20, height=20):
                    ui.Rectangle(style=STYLE_BUTTON_VISIBILITY)
                    icon_name = "visibility_on" if is_visible else "visibility_off"
                    image_provider = ui.VectorImageProvider(source_url=get_icon_path(icon_name))
                    button = ui.ImageWithProvider(
                        image_provider, width=20, height=20, style=STYLE_BUTTON_VISIBILITY, identifier="VisibilityBtn"
                    )
                    button.checked = not is_visible
                    button.set_mouse_pressed_fn(
                        lambda x, y, btn, m, b=button, i=image_provider, uuid=item.uuid: self._on_visibility_clicked(
                            b, i, uuid
                        )
                    )
                self.__ui_cache[item.payload.uuid].visibility_btn = button

            elif column_id == 1:  # Go to
                with ui.ZStack(width=20, height=20):
                    ui.Rectangle(style=STYLE_BUTTON_GO_TO)
                    button = ui.ImageWithProvider(
                        ui.VectorImageProvider(source_url=get_icon_path("go_to")),
                        width=20,
                        height=20,
                        style=STYLE_BUTTON_GO_TO,
                        identifier="GotoBtn",
                    )
                    button.set_mouse_pressed_fn(
                        lambda x, y, btn, m, b=button, uuid=item.uuid: self._on_go_to_clicked(b, uuid)
                    )
                self.__ui_cache[item.payload.uuid].go_to_btn = button

            elif column_id == 2:  # Name
                label_stack = ui.ZStack(height=20)
                with label_stack:
                    label = ui.Label(item.payload.name, height=20, elided_text=True)
                    field = ui.StringField(None, visible=False)
                    field.model.as_string = item.payload.name
                label_stack.set_mouse_double_clicked_fn(
                    lambda x, y, b, m, f=field, l=label, u=item.payload.uuid: self._on_label_click(b, f, l, u)
                )
                self.__ui_cache[item.payload.uuid].name_field = field

            elif column_id == 3:  # Primary Value
                precision = list(Precision).index(item.payload.precision.value)
                if item.payload.tool_mode in [MeasureMode.ANGLE, MeasureMode.AREA]:
                    unit_type = (
                        "°"
                        if item.payload.tool_mode == MeasureMode.ANGLE
                        else f"{item.payload.unit_type.name.title()}²"
                    )
                else:
                    unit_type = item.payload.unit_type.name.title()

                ui.Label(
                    f"{item.payload.primary_value:.{precision}f} {unit_type}",
                    alignment=ui.Alignment.RIGHT_CENTER,
                    height=20,
                    elided_text=True,
                )

            elif column_id == 4:  # Item Type (Image)
                tool_name = item.payload.tool_mode.name.lower()
                icon_path = get_icon_path(f"tool_{tool_name}")
                with ui.HStack():
                    ui.Spacer()
                    image = ui.ImageWithProvider(ui.VectorImageProvider(source_url=icon_path), width=20, height=20)
                    ui.Spacer()
                    self.__ui_cache[item.payload.uuid].type_img = image

            elif column_id == 5:  # Delete Item
                with ui.HStack():
                    ui.Spacer()
                    with ui.ZStack(width=20, height=20):
                        ui.Rectangle(style=STYLE_BUTTON_DELETE)
                        button = ui.ImageWithProvider(
                            ui.VectorImageProvider(source_url=get_icon_path("tool_delete")),
                            width=20,
                            height=20,
                            style=STYLE_BUTTON_DELETE,
                            identifier="DeleteBtn",
                        )
                        button.set_mouse_pressed_fn(lambda x, y, btn, m, uuid=item.uuid: self._on_delete_clicked(uuid))
                    ui.Spacer()
                    self.__ui_cache[item.payload.uuid].delete_btn = button

        elif level == 2 and issubclass(item.__class__, MeasureSubItem):
            if column_id == 1:
                ui.Label(item.name, height=20, alignment=ui.Alignment.RIGHT_CENTER, elided_text=False)

            elif column_id == 2:
                ui.Label(str(item.value), height=20, alignment=ui.Alignment.RIGHT_CENTER, elided_text=True)
