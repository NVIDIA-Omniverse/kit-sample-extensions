import functools
import weakref

import AnimationSchema
import carb
import omni.anim.curve.core as curve
import omni.graph.core as og
import omni.ui as ui
import omni.usd
from omni.kit.widget.stage import StageIcons
from pxr import Sdf, Tf, Usd, UsdUtils

from .curve_editor import SingletonCurveEditor
from .curve_editor_curves import CurveListView
from .curve_editor_globals import (
    CurveInterpolation,
    get_component_and_attribute_name_and_prim,
    get_curve_from_runtime,
    get_runtime_style_attribute_name,
)

DEFAULT_TANGENT_TYPE_ICON_SIZE = 20
COLUMN1_WIDTH = (
    DEFAULT_TANGENT_TYPE_ICON_SIZE  # SPLITTER_WIDTH is 10, but +8 seems the best fit though I do not know why
)

SEARCH_BAR_TEXT = ""  # since Andrew's MR makes the search bar being rebuilt each time the curve editor re-draws,
# we have to use some hack to make things work, instead of using the standard 'model-view' model


class _PanelItem(ui.AbstractItem):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.children = []


class _TreeDelegatee(ui.AbstractItemDelegate):
    def __init__(self, curve_editor_view):
        super().__init__()
        self._curve_editor_view_wp = weakref.ref(curve_editor_view)
        self._pushed_menu = None
        self._pushed_menu_widget = None

        self.indent_width = 15
        # these special cases must contain whitespace or parenthese. To tell that these are not general usd attributes. Usd attribute name does not allow whitespace and parenthese.
        self._display_convert_map = {
            "xformOp:scale:x": "Scale X",
            "xformOp:scale:y": "Scale Y",
            "xformOp:scale:z": "Scale Z",
            "xformOp:rotateX:x": "Rotate(X)",
            "xformOp:rotateY:x": "Rotate(Y)",
            "xformOp:rotateZ:x": "Rotate(Z)",
            "xformOp:rotateXYZ:x": "Rotate X",  # this is the most frequently used case for rotate
            "xformOp:rotateXYZ:y": "Rotate Y",  # this is the most frequently used case for rotate
            "xformOp:rotateXYZ:z": "Rotate Z",  # this is the most frequently used case for rotate
            "xformOp:rotateXZY:x": "Rotate(XZY) X",
            "xformOp:rotateXZY:y": "Rotate(XZY) Y",
            "xformOp:rotateXZY:z": "Rotate(XZY) Z",
            "xformOp:rotateYXZ:x": "Rotate(YXZ) X",
            "xformOp:rotateYXZ:y": "Rotate(YXZ) Y",
            "xformOp:rotateYXZ:z": "Rotate(YXZ) Z",
            "xformOp:rotateYZX:x": "Rotate(YZX) X",
            "xformOp:rotateYZX:y": "Rotate(YZX) Y",
            "xformOp:rotateYZX:z": "Rotate(YZX) Z",
            "xformOp:rotateZXY:x": "Rotate(ZXY) X",
            "xformOp:rotateZXY:y": "Rotate(ZXY) Y",
            "xformOp:rotateZXY:z": "Rotate(ZXY) Z",
            "xformOp:rotateZYX:x": "Rotate(ZYX) X",
            "xformOp:rotateZYX:y": "Rotate(ZYX) Y",
            "xformOp:rotateZYX:z": "Rotate(ZYX) Z",
            "xformOp:translate:x": "Translate X",
            "xformOp:translate:y": "Translate Y",
            "xformOp:translate:z": "Translate Z",
            "Translate:x": "Translate::X",
            "Translate:y": "Translate::Y",
            "Translate:z": "Translate::Z",
            "Rotate:x": "Rotate::X",
            "Rotate:y": "Rotate::Y",
            "Rotate:z": "Rotate::Z",
            "Scale:x": "Scale::X",
            "Scale:y": "Scale::Y",
            "Scale:z": "Scale::Z",
        }

    def _get_curve_editor_icon_path(self, icon_file_name):
        return f"{self._curve_editor_view_wp()._icon_path}/{icon_file_name}"

    def _get_image_url_from_tangent_type(self, index):
        resources = [
            "auto_tangent.svg",
            "smooth_tangent.svg",
            "flat_tangent.svg",
            "fixed_tangent.svg",
            "linear_tangent.svg",
            "step_tangent.svg",
        ]
        return self._get_curve_editor_icon_path(resources[index])

    def _usd_edit_scope(self):
        return self._curve_editor_view_wp().get_internal_usd_edit_scope()

    def _get_default_tangent_type_from_runtime(self, stage, curve_path) -> CurveInterpolation.TangentType:
        component_char, attr_name, prim_path_str = get_component_and_attribute_name_and_prim(str(curve_path))
        curve_name = attr_name + ":" + component_char
        runtime_curve = get_curve_from_runtime(prim_path_str, curve_name)
        if runtime_curve != None:
            schema_curve_api = AnimationSchema.AnimationCurveAPI(stage.GetPrimAtPath(runtime_curve.anim_data))
        else:
            carb.log_error("Unexpected code path in _TreeDelegatee._get_default_tangent_type_from_runtime()")
            return ""

        tangent_type_token = schema_curve_api.GetDefaultTangentType(curve_name)
        return CurveInterpolation.TangentType.get(tangent_type_token)

    def _on_default_tangent_type_change(self, curve_track_name: str, widget, tangent_type_index):
        with self._usd_edit_scope():
            omni.kit.commands.execute(
                "SetAnimCurveDefaultTangentType",
                paths=[get_runtime_style_attribute_name(curve_track_name)],
                default_tangent_type=CurveInterpolation.TangentType.to_tangent_type_token(tangent_type_index),
            )

        widget.image_url = self._get_image_url_from_tangent_type(tangent_type_index)

    def _show_pushed_menu(self, x, y, button, modifier, widget, curve_track_name: str):
        # Display context menu only if the left mouse button is pressed
        if button != 0:
            return

        # toggle menu show/hide, by clicking on the button again
        if self._pushed_menu_widget == widget and self._pushed_menu.shown:
            self._pushed_menu.hide()
            return

        self._pushed_menu_widget = widget
        self._pushed_menu = ui.Menu(
            "Pushed menu",
            #            style={
            #                "Menu": {"background_color": 0xFF000000, "color": 0xFFFFFFFF, "background_selected_color": 0xFFAAAAAA},
            #                "MenuItem": {"color": 0xFFFFFFFF, "background_selected_color": 0xFFAAAAAA},
            #            },
        )

        tangent_type_index = self._get_default_tangent_type_from_runtime(
            omni.usd.get_context().get_stage(), curve_track_name
        )
        # Reset the previous context popup
        self._pushed_menu.clear()
        with self._pushed_menu:
            for i in range(len(CurveInterpolation.TangentTypeTokens)):
                # skip over Fixed type from the UI perspective
                if i == CurveInterpolation.TangentType.Fixed:
                    continue
                checked = tangent_type_index == i
                ui.MenuItem(
                    CurveInterpolation.TangentTypeTokens[i],
                    checkable=True,
                    checked=checked,
                    # if it is already checked, empty trigger function to avoid unnecessary command execution.
                    triggered_fn=(
                        None
                        if checked
                        else (
                            lambda curve_track_name=curve_track_name, widget=widget, tangent_type_index=i: self._on_default_tangent_type_change(
                                curve_track_name, widget, tangent_type_index
                            )
                        )
                    ),
                )

        # Show it
        self._pushed_menu.show_at(
            (int)(widget.screen_position_x), (int)(widget.screen_position_y + widget.computed_content_height)
        )

    # usd attribute name does not allow double colon. So these converted names are diffrent from other general usd attribute names.
    def _get_display_name_generic_attribute(self, short_track_name, full_path):
        string_pre, sep, string_post = short_track_name.rpartition(":")
        # if find the separator
        if sep == ":":
            full_attr_path, _, _ = full_path.pathString.rpartition(":")
            attr = omni.usd.get_context().get_stage().GetAttributeAtPath(full_attr_path)
            scalar_type_names = [
                Sdf.ValueTypeNames.Double,
                Sdf.ValueTypeNames.Float,
                Sdf.ValueTypeNames.Half,
                Sdf.ValueTypeNames.Int,
                Sdf.ValueTypeNames.UInt,
                Sdf.ValueTypeNames.Int64,
                Sdf.ValueTypeNames.UInt64,
                Sdf.ValueTypeNames.Bool,
                Sdf.ValueTypeNames.Token,
            ]
            # scalar attribute use original name
            if attr and attr.GetTypeName() in scalar_type_names:
                return string_pre
            else:
                # vector attribute use whitespace as the separator
                if string_post == "x":
                    return string_pre + " X"
                if string_post == "y":
                    return string_pre + " Y"
                if string_post == "z":
                    return string_pre + " Z"
                if string_post == "w":
                    return string_pre + " W"

        carb.log_error("Unexpected code path in _TreeDelegatee._get_display_name_generic_attribute()")
        return short_track_name

    def _get_more_readable_string(self, short_track_name, full_attr_path):
        display_name = self._display_convert_map.get(short_track_name)
        if display_name == None:
            display_name = self._get_display_name_generic_attribute(short_track_name, full_attr_path)
        return display_name

    def build_branch(self, model, item, column_id, level, expanded):
        if column_id == 0:
            with ui.HStack():
                ui.Spacer(width=self.indent_width * level)
                if model.can_item_have_children(item):
                    image_name = "Minus" if expanded else "Plus"
                    ui.Image(
                        str(StageIcons().get(image_name)),
                        width=self.indent_width,
                        height=10,
                        style_type_name_override="TreeView.Item",
                    )

    # Build a widget for an Item. PrimItem or AttrItem
    def build_widget(self, model, item, column_id, level, expanded):
        # In some cases in Unit test the stage is None early out.
        if omni.usd.get_context() is None or omni.usd.get_context().get_stage() is None:
            return
        """Create a widget per column per item"""
        if item.path.IsPrimPath():
            if column_id == 0:
                with ui.HStack():
                    # Prim is always built no matter what is in the search bar
                    prim_type = None
                    prim = omni.usd.get_context().get_stage().GetPrimAtPath(item.path)
                    if prim:
                        prim_type = prim.GetTypeName()

                    icon = StageIcons().get(prim_type, "Prim")
                    ui.Image(
                        str(icon),
                        width=self.indent_width,
                        height=self.indent_width,
                        style_type_name_override="TreeView.Image",
                    )
                    label = ui.Label(str(item.path.name), style_type_name_override="TreeView.Item")
                    label.set_tooltip(str(item.path))
            elif column_id == 1:
                with ui.ZStack(height=0):
                    # Min size
                    ui.Spacer(width=DEFAULT_TANGENT_TYPE_ICON_SIZE)
        else:
            # if search bar is not empty, then only show those related paths
            if SEARCH_BAR_TEXT and SEARCH_BAR_TEXT not in self._get_more_readable_string(item.path.name, item.path):
                return

            if column_id == 0:
                with ui.HStack():
                    ui.Spacer(width=self.indent_width)
                    ext_path = (
                        omni.kit.app.get_app()
                        .get_extension_manager()
                        .get_extension_path_by_module("omni.kit.property.usd")
                    )
                    ui.Image(
                        str(ext_path + "/data/icons/Animation Curve.svg"),
                        width=self.indent_width,
                        height=self.indent_width,
                        style_type_name_override="TreeView.Image",
                    )
                    label = ui.Label(
                        self._get_more_readable_string(item.path.name, item.path),
                        style_type_name_override="TreeView.Item",
                    )

                    color = self._curve_editor_view_wp().get_curve_color(str(item.path.name))

                    label.style = {"color": color}
            elif column_id == 1:
                curve_track_name = str(item.path)
                tangent_type_index = self._get_default_tangent_type_from_runtime(
                    omni.usd.get_context().get_stage(), curve_track_name
                )
                bt = ui.Button(
                    "",
                    width=0,
                    height=0,
                    image_url=self._get_image_url_from_tangent_type(tangent_type_index),
                    image_width=DEFAULT_TANGENT_TYPE_ICON_SIZE,
                    image_height=DEFAULT_TANGENT_TYPE_ICON_SIZE,
                    style={"margin_height": 0, "margin_width": 0, "padding": 0, "background_color": 0x00000000},
                )
                bt.set_mouse_pressed_fn(
                    lambda x, y, b, m, widget=bt, curve_track_name=curve_track_name: self._show_pushed_menu(
                        x, y, b, m, widget, curve_track_name
                    )
                )

    def build_header(self, column_id):
        pass


class _PrimPanelModel(ui.AbstractItemModel):
    def __init__(self, curve_editor_view):
        super().__init__()
        self._curve_editor_view_wp = weakref.ref(curve_editor_view)

        self._selected_only = True
        self._prims = []

        if not self._selected_only:
            self._stage_update_sub = omni.stageupdate.get_stage_update_interface().create_stage_update_node(
                "CurveEditorPrimPanel",
                on_attach_fn=functools.partial(__class__._on_stage_attach, weakref.proxy(self)),
                on_detach_fn=functools.partial(__class__._on_stage_detach, weakref.proxy(self)),
            )

        self._curve_event_sub = (
            curve.get_curve_plugin()
            .get_event_stream()
            .create_subscription_to_pop(functools.partial(__class__._on_curve_event, weakref.proxy(self)))
        )

        self.on_prim_list_changed = None

    def _usd_edit_scope(self):
        return self._curve_editor_view_wp().get_internal_usd_edit_scope()

    def _on_curve_event_added(self, event):
        selection = omni.usd.get_context().get_selection()
        selection_paths = selection.get_selected_prim_paths()
        event_paths = event.payload["paths"]
        for path in event_paths:
            path = Sdf.Path(path)
            prim_path = path.GetPrimPath()
            if prim_path in selection_paths:
                self._add_item(path)

    def _on_curve_event_removed(self, event):
        event_paths = event.payload["paths"]
        for path in event_paths:
            self._remove_item(Sdf.Path(path))

    def _on_curve_event(self, event):
        if event.type == curve.CurveEventType.Added:
            self._on_curve_event_added(event)
        elif event.type == curve.CurveEventType.Removed:
            self._on_curve_event_removed(event)
        elif event.type == curve.CurveEventType.Updated:
            # if edit scope is not occupied by internal operation.
            if self._usd_edit_scope():
                self._on_curve_event_removed(event)
                self._on_curve_event_added(event)

    def _on_stage_attach(self, stage_id, meters_per_unit):
        cache = UsdUtils.StageCache.Get()
        stage = cache.Find(Usd.StageCache.Id.FromLongInt(stage_id))

    def _on_stage_detach(self):
        stage = None

    def _remove_item(self, path):
        if path.IsPrimPath():
            for item in self._prims:
                if item.path != path:
                    continue

                self._prims.remove(item)
                self._item_changed(None)
                self.on_prim_list_changed()
                return
        elif path.IsPropertyPath():
            for item in self._prims:
                if item.path != path.GetPrimPath():
                    continue

                for curve_item in item.children:
                    if curve_item.path != path:
                        continue

                    item.children.remove(curve_item)
                    self._item_changed(item)
                    return

    def _add_item(self, path):
        if path.IsPrimPath():
            for item in self._prims:
                if item.path == path:
                    return

            curve_prims = curve.get_curve_plugin().get_curve_prims(str(path))
            if not curve_prims:
                return

            timeline = False

            node = og.get_node_by_path(str(path))
            if node is not None:
                timeline = node.get_node_type().get_node_type() == "omni.anim.Timeline"

            curves = curve.get_curve_plugin().get_curves(str(path))
            if not curves and not timeline:
                return

            prim_item = _PanelItem(path)
            self._prims.append(prim_item)

            self._item_changed(None)
            self.on_prim_list_changed()

            for curve_name in curves.keys():
                self._add_item(path.AppendProperty(curve_name))
        elif path.IsPropertyPath():
            for item in self._prims:
                if item.path != path.GetPrimPath():
                    continue

                curve_item = _PanelItem(path)
                item.children.append(curve_item)

                def key_func(item):
                    name = str(item.path.name)
                    index = None
                    if name.startswith("xformOp:translate"):
                        index = 0
                    elif name.startswith("xformOp:rotate"):
                        index = 1
                    elif name.startswith("xformOp:scale"):
                        index = 2
                    else:
                        index = 3
                    return str(index) + name

                item.children.sort(key=key_func)
                self._item_changed(item)
                break

    def select_prims(self, paths):
        self._prims.clear()
        self._item_changed(None)
        self.on_prim_list_changed()

        stage = omni.usd.get_context().get_stage()

        for path in paths:
            prim = stage.GetPrimAtPath(path)
            if not prim:
                continue

            self._add_item(prim.GetPath())

    def get_item_value_model_count(self, item):
        return 2

    def get_item_children(self, item):
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return []

        if item is None:
            timeline_node_prims = []

            for item in self._prims:
                prim = stage.GetPrimAtPath(item.path)
                if (
                    prim.GetTypeName() in ("OmniGraphNode", "ComputeNode")
                    and prim.GetAttribute("node:type").Get() == "omni.anim.Timeline"
                ):
                    timeline_node_prims.append(item)

            if len(timeline_node_prims) == len(self._prims):
                return self._prims[0:1]
            else:
                items = []
                for item in self._prims:
                    if not item in timeline_node_prims:
                        items.append(item)
                return items
        else:
            return item.children

    def get_item_value_model(self, item, column_id):
        label = None
        if item.path.IsPrimPath():
            label = item.path
        else:
            label = item.path.name

        return ui.SimpleStringModel(str(label))


# a dummy event
class SelectionChangedEvent:
    def __init__(self):
        self.type = int(omni.usd.StageEventType.SELECTION_CHANGED)


class PrimPanel(ui.ScrollingFrame):
    def __init__(self, curve_editor_view):

        super().__init__(style_type_name_override="TreeView", name="primPanel")

        self._curve_editor_view_wp = weakref.ref(curve_editor_view)

        self._selecting_in_tree_view = False

        self._stage_event_sub = (
            omni.usd.get_context()
            .get_stage_event_stream()
            .create_subscription_to_pop(
                functools.partial(__class__._on_stage_event, weakref.proxy(self)), name="Curve editor Prim Panel"
            )
        )

        with self:
            with ui.ZStack():
                self._build_doc()
                self._build_tree()

    def _on_prim_list_changed(self):
        show_doc = len(self._prim_panel_model._prims) == 0
        self._doc_frame.visible = show_doc
        self._tree_view.visible = not show_doc

    def _build_doc(self):
        self._doc_frame = ui.VStack()
        with self._doc_frame:
            ui.Spacer(height=20)
            ui.Image(f"{self._curve_editor_view_wp()._icon_path}/leftPanelDoc.png", height=95)
            ui.Label("Select Any Animated Prims", alignment=ui.Alignment.CENTER, height=30, style={"color": 0xFF8A8777})
            # ui.Label("Document", alignment=ui.Alignment.CENTER, height=20)

    def _build_tree(self):
        self._prim_panel_model = _PrimPanelModel(self._curve_editor_view_wp())
        self._prim_panel_model.on_prim_list_changed = self._on_prim_list_changed
        self._tree_delegate = _TreeDelegatee(self._curve_editor_view_wp())
        self._tree_view = ui.TreeView(
            self._prim_panel_model,
            delegate=self._tree_delegate,
            root_visible=False,
            columns_resizable=False,
            style={
                "TreeView": {
                    "background_color": 0xFF23211F,
                    "background_selected_color": 0x664F4D43,
                    "secondary_color": 0xFF403B3B,
                },
                "TreeView.ScrollingFrame": {"background_color": 0xFF23211F},
                "TreeView.Header": {"background_color": 0xFF343432, "color": 0xFFCCCCCC, "font_size": 12},
                # "TreeView.Header::visibility_header": {"image_url": StageIcons().get("eye_header")},
                "TreeView.Image::object_icon_grey": {"color": 0x80FFFFFF},
                "TreeView.Image:disabled": {"color": 0x60FFFFFF},
                "TreeView.Item": {"color": 0xFF8A8777},
                "TreeView.Item:disabled": {"color": 0x608A8777},
                "TreeView.Item::object_name_grey": {"color": 0xFF4D4B42},
                "TreeView.Item::object_name_missing": {"color": 0xFF6F72FF},
                "TreeView.Item:selected": {"color": 0xFF23211F},
                "TreeView:selected": {"background_color": 0xFF8A8777},
            },
        )

        self._tree_view.column_widths = [ui.Fraction(1), ui.Pixel(COLUMN1_WIDTH)]
        self._tree_view.keep_expanded = self._prim_panel_model._selected_only

        self._on_stage_event(SelectionChangedEvent())

        self._tree_view.set_selection_changed_fn(self._on_tree_selection_changed)

    def _on_tree_selection_changed(self, items):
        if self._selecting_in_tree_view:
            return

        selection = omni.usd.get_context().get_selection()
        if not items:
            if not self._prim_panel_model._selected_only:
                selection.set_selected_prim_paths([], True)
                return

        prims = []
        attrs = []
        for item in items:
            if item.path.IsPrimPath():
                prims.append(item.path)
            elif item.path.IsPropertyPath():
                attrs.append(item.path)

        if not self._prim_panel_model._selected_only:
            selection.set_selected_prim_paths([str(prim)], True)

        editor = SingletonCurveEditor.get_instance()
        tracks = editor.get_tracks()
        for track in tracks:
            track_path = Sdf.Path(track.get_track_name())
            if track.get_prim_path_str() in prims or track_path in attrs:
                editor.set_track_is_visible(track, True)
            else:
                editor.set_track_is_visible(track, False)

    def _on_stage_event(self, event):
        if event.type != int(omni.usd.StageEventType.SELECTION_CHANGED):
            return

        if hasattr(event, "search_bar_text"):
            global SEARCH_BAR_TEXT
            SEARCH_BAR_TEXT = event.search_bar_text

        selection = omni.usd.get_context().get_selection()
        paths = selection.get_selected_prim_paths()

        if self._prim_panel_model._selected_only:
            self._prim_panel_model.select_prims(paths)
            self._tree_view.selection = self._prim_panel_model._prims
        else:
            # Remove unselected
            tree_selection = self._tree_view.selection

            new_selection = []
            selected_key_attr = False

            for item in tree_selection:
                if item.path in paths:
                    new_selection.append(item)
                elif item.prim is not None and item.prim in paths:
                    new_selection.append(item)
                    selected_key_attr = True

            # Select the prim if any of its key attributes are not selected
            if not selected_key_attr:
                for item in self._prim_panel_model._prims:
                    if item.path in paths:
                        new_selection.append(item)

            if not self._prim_panel_model._selected_only:
                self._selecting_in_tree_view = True
            self._tree_view.selection = new_selection
            self._selecting_in_tree_view = False
