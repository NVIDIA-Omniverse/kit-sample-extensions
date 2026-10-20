from typing import Union

import carb
import omni.ui as ui
from carb.dictionary import ItemType
from omni.kit.widget.settings import SettingType, create_setting_widget

from .model import SettingPathItem, SettingsModel, SettingValueItem

FULL_LINE_HEIGHT = 26


class VLine(ui.Line):
    def __init__(self, half: bool = False, item=None):
        count = 1
        if item and isinstance(item, SettingValueItem):
            if isinstance(item.value, list) or isinstance(item.value, tuple):
                count = len(item.value)
        height = FULL_LINE_HEIGHT * count
        super().__init__(
            height=height / 2 if half else height,
            width=0,
            alignment=ui.Alignment.LEFT,
            style_type_name_override="TreeView.Branch.Line",
        )


class SettingTreeDelegate(ui.AbstractItemDelegate):
    def build_widget(
        self,
        model: ui.AbstractItemModel,
        item: Union[SettingPathItem, SettingValueItem],
        index: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        if isinstance(item, SettingPathItem):
            if index == 0:
                with ui.VStack(height=20):
                    ui.Label(f"{item.name} ({item.count})", style_type_name_override="TreeView.Item.Name")
        elif isinstance(item, SettingValueItem):
            if index == 0:
                ui.Label(
                    f"{item.name}",
                    alignment=ui.Alignment.TOP,
                    tooltip=item.path,
                    style_type_name_override="TreeView.Item.Name",
                )
            else:
                with ui.VStack():
                    ui.Spacer(height=1)
                    match item.setting_type:
                        case ItemType.BOOL:
                            create_setting_widget(item.path, SettingType.BOOL)
                        case ItemType.INT:
                            create_setting_widget(item.path, SettingType.INT)
                        case ItemType.FLOAT:
                            create_setting_widget(item.path, SettingType.FLOAT)
                        case ItemType.STRING:
                            create_setting_widget(item.path, SettingType.STRING)
                        case ItemType.DICTIONARY:
                            if not item.value:
                                ui.Label("{}")
                            elif isinstance(item.value, list) or isinstance(item.value, tuple):
                                self._create_list_widget(item)
                            else:
                                carb.log_warn(f"Unknown value type {type(item.value)}: {item.path}, {item.value}")
                        case _:
                            carb.log_warn(f"UNKNOWN type: {item.setting_type} from {item.path}: {item.value}")
                            ui.Label(str(item.setting_type), style_type_name_override="TreeView.Item.Name")
                    ui.Spacer(height=1)

    def build_branch(
        self,
        model: ui.AbstractItemModel,
        item: Union[SettingPathItem, SettingValueItem],
        column_id: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        """
        Create a branch widget that opens or closes subtree
        Args:
            model (AbstractItemModel): Category data model
            item (CategoryItem): Category item
            column_id (int): ignore
            level (int): Level of the hierarchy the current item is at, from 0 to n.
            expand (int): Indicates whether we will see child categories expanded or not.
        """
        if column_id != 0:
            return

        with ui.HStack(spacing=0):
            ui.Spacer(width=5)  # Extra left margin for all

            if isinstance(item, SettingValueItem):
                ui.Spacer(width=2)

                if level == 0:
                    # Just a simple dot
                    ui.Circle(
                        width=4, alignment=ui.Alignment.RIGHT_CENTER, style_type_name_override="TreeView.Branch.Line"
                    )
                    ui.Spacer(width=8)
                    return

                ui.Spacer(width=3)
                if level > 1:
                    for _ in range(1, level):
                        VLine(item=item)
                        ui.Spacer(width=15)

                with ui.ZStack():
                    # vertical line
                    with ui.HStack():
                        if not hasattr(item, "is_last_child") or not item.is_last_child:
                            # Full vertical line
                            VLine(item=item)
                        else:
                            # Half vertical line for L-shaped branch
                            with ui.VStack():
                                VLine(half=True, item=item)
                                ui.Spacer(height=6)
                        ui.Spacer()

                    # horiz line
                    ui.Line(width=16, style_type_name_override="TreeView.Branch.Line")

                    # dot
                    with ui.HStack():
                        ui.Spacer()
                        ui.Circle(
                            width=4,
                            alignment=ui.Alignment.RIGHT_CENTER,
                            style_type_name_override="TreeView.Branch.Line",
                        )

                ui.Spacer(width=10)  # more space after dot than +/-

            else:
                if level > 0:
                    item.children[-1].is_last_child = True

                    ui.Spacer(width=5)
                    for i in range(0, level):
                        # OM-83328: Always show line here
                        VLine(item=item)
                        if i != level - 1:
                            ui.Spacer(width=15)
                    ui.Spacer(width=10)

                self._draw_expanded_symbol(expanded)

    def _draw_expanded_symbol(self, expanded: bool) -> None:
        if expanded:
            # Minus sign
            with ui.VStack(width=8):
                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Spacer(width=2)
                    ui.Line(width=7, style_type_name_override="TreeView.Item")
                ui.Spacer()
        else:
            # Plus sign
            with ui.ZStack(width=8):
                # horiz line
                with ui.VStack(width=8):
                    ui.Spacer()
                    with ui.HStack():
                        ui.Spacer(width=2)
                        ui.Line(width=7, style_type_name_override="TreeView.Item")
                    ui.Spacer()
                # vertical line
                with ui.HStack():
                    ui.Spacer(width=1)
                    ui.Spacer()
                    with ui.VStack():
                        ui.Spacer(height=0.1)
                        ui.Spacer()
                        ui.Line(height=7, alignment=ui.Alignment.H_CENTER, style_type_name_override="TreeView.Item")
                        ui.Spacer()
                    ui.Spacer()
        ui.Spacer(width=5)

    def _create_list_widget(self, item: SettingValueItem):
        models = item.create_sub_value_models()
        with ui.VStack(spacing=1):
            for model in models:
                if isinstance(model, ui.SimpleStringModel):
                    ui.StringField(model)
                elif isinstance(model, ui.SimpleIntModel):
                    ui.IntDrag(model)
                elif isinstance(model, ui.SimpleFloatModel):
                    ui.FloatDrag(model)
                else:
                    carb.log_warn(f"Failed to create widget for {model} from {item.path}")


class SettingsView:
    def __init__(self, model: SettingsModel):
        with ui.ScrollingFrame():
            self._delegate = SettingTreeDelegate()
            ui.TreeView(
                model,
                delegate=self._delegate,
                root_visible=False,
                expand_on_branch_click=True,
                column_widths=[300, ui.Fraction(1)],
                columns_resizable=True,
            )
