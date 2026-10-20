# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import weakref

import carb
import omni.kit.context_menu as cm
import omni.kit.menu.utils as menu_utils
import omni.kit.notification_manager as nm
import omni.kit.usd.layers as layers
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.menu.utils import MenuItemDescription
from pxr import Sdf

from . import editor_const as e_c
from . import ui_const as ui_c
from .core import VariantEditorCore
from .picker import RootSelector, StageWindowButton
from .prim_property_tree import PrimPropertyDelegate, PrimPropertyView
from .stage_change_helper import StageChangeHelper
from .variant_tree import VariantTreeDelegate, VariantTreeModel, VariantTreeView
from .variant_tree_items import PrimCardItem, VariantCardItem, VariantSetCardItem

try:
    from omni.kit.usd.layers import layer_event_name

    _is_legacy_layer_event = False
except ImportError:
    _is_legacy_layer_event = True


class VariantEditorWindow(StageChangeHelper):
    _variant_editor_window_instance = None

    @staticmethod
    def get_instance():
        if VariantEditorWindow._variant_editor_window_instance is None:
            VariantEditorWindow._variant_editor_window_instance = VariantEditorWindow()
        return VariantEditorWindow._variant_editor_window_instance

    def __init__(self):
        super().__init__()

        self._window = None
        self._options_menu = None
        self._menu_root = None
        self._menu_entry_items = []
        self._prim_list_screen = None
        self._guide_label = None
        self._stage_context_menu_sub = None
        self._stage_context_menu_sub = None

        self._create_menu_entry()

        self._editor_core = None

        # Connect to Content Stage Window, Property Window and Content Browser for quick add/access options
        self.__connect_content_browser()
        self.__connect_stage_window()
        self.__connect_property_window()

        # Setup stage/usd/omni references
        self._usd_context = omni.usd.get_context()
        self._stage = None

        # Variant tree model will be initialized when stage is opened
        self._variant_tree_model = None

        self._reset_ui_object_refs()

        # Initialize views and delegates
        self._variant_tree_view = None
        self._variant_tree_delegate = VariantTreeDelegate()

        self._prim_property_tree_view = None
        self._prim_property_tree_delegate = PrimPropertyDelegate()

        self._closed_via_button = False

        self._variant_tree_model_changed_fn = None

        # Subscribe to stage events
        self._stage_event_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.variant.editor.VariantEditorWindow:Stage",
                event_name=self._usd_context.stage_event_name(event),
                on_event=func,
            )
            for event, func in (
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_opened()),
                (omni.usd.StageEventType.CLOSING, lambda _: self._on_stage_closed()),
            )
        ]

        # Subscribe to layer switching events
        self._layer_event_sub = None

        # If the stage is already open with this is initialized, call _on_stage_opened
        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:
            self._on_stage_opened()

    def destroy(self):
        self.hide()
        self._reset_ui_object_refs()
        self._window = None
        self.__disconnect_stage_window()
        self.__disconnect_content_browser()
        self.__disconnect_property_window()

        if self._editor_core is not None:
            self._editor_core.destroy()
            self._editor_core = None

        if self._variant_tree_delegate:
            self._variant_tree_delegate = None

        if self._prim_property_tree_delegate:
            self._prim_property_tree_delegate = None

        if self._variant_tree_view is not None:
            self._variant_tree_view.destroy()
            self._variant_tree_view = None

        if self._prim_property_tree_view is not None:
            self._prim_property_tree_view.destroy()
            self._prim_property_tree_view = None

        if self._variant_tree_model_changed_fn is not None:
            self._variant_tree_model.remove_item_changed_fn(self._variant_tree_model_changed_fn)
            self._variant_tree_model_changed_fn = None

        if self._variant_tree_model is not None:
            self._variant_tree_model.destroy()
            self._variant_tree_model = None

        if self._options_menu is not None:
            self._options_menu.destroy()
            self._options_menu = None

        StageChangeHelper.disable()

        # Unsubscribe from stage events
        self._stage_event_subs.clear()
        self._stage_event_subs = None
        self._layer_event_sub = None

        self._menu_entry_items.clear()
        menu_utils.remove_menu_items(self._menu_root, "Tools")
        self._menu_root = None

    # TODO: Probably several other widgets I should be making sure to clean up across the main window, four lists, and various pickers
    def _reset_ui_object_refs(self):
        self._variant_set_path_field = None
        self._prim_list_screen = None
        self._guide_label = None

    # Hide and clean window when changing stages
    def _on_stage_opened(self):
        if self._editor_core is None:
            self._editor_core = VariantEditorCore.get_instance()
            self._editor_core.bind_to(self._update_guide_label)

        self._editor_core._update_context_and_stage()

        # Set up model and views
        if self._variant_tree_model is None:
            self._variant_tree_model = VariantTreeModel()
        else:
            self._variant_tree_model.reset_expanded()

        self._variant_tree_model_changed_fn = self._variant_tree_model.add_item_changed_fn(self.set_tree_view_expanded)

        # If tree views already exists, assign model to them
        if self._variant_tree_view:
            self._variant_tree_view._tree_view.model = self._variant_tree_model

        if self._prim_property_tree_view:
            self._prim_property_tree_view._tree_view.model = self._variant_tree_model

        # Subscribe to layer events.
        # Resolve the context from the stage rather than reusing the cached one:
        # get_context_from_stage() resolves through C++, so it still yields a real
        # UsdContext when omni.usd.get_context has been replaced at the Python level
        # by a test harness (OMPE-105547). Fall back to the cached context, then guard.
        self._layer_event_sub = None
        usd_context = None
        stage = self._editor_core._stage
        if stage:
            try:
                usd_context = omni.usd.get_context_from_stage(stage)
            except Exception:
                # get_context_from_stage() falls back to stage.GetStageId() when the StageCache
                # lookup raises, and a plain Usd.Stage has no such method. Never let resolving a
                # context take down the stage-opened handler.
                carb.log_info("Variant Editor could not resolve a context from the current stage.")
        usd_context = usd_context or self._editor_core._usd_context
        layer_interface = layers.get_layers(usd_context)
        if layer_interface is None:
            # get_layers() has already logged a warning explaining the rejection; keep this
            # at info level so a single event does not produce two warnings.
            carb.log_info("Variant Editor could not resolve a Layers interface; layer events are not tracked.")
        elif _is_legacy_layer_event:
            self._layer_event_sub = layer_interface.get_event_stream().create_subscription_to_pop(
                self._on_layer_events, name="Variant Editor Window"
            )
        else:
            self._layer_event_sub = get_eventdispatcher().observe_event(
                observer_name="omni.kit.variant.editor.VariantEditorWindow:Layer",
                event_name=layers.layer_event_name(layers.LayerEventType.EDIT_TARGET_CHANGED),
                on_event=self._on_layer_edit_target_changed,
                filter=layer_interface.get_event_key(),
            )

        if self._window:
            if self._window.visible:
                self._reset_to_defaults()

    def _on_stage_closed(self):
        if self._variant_tree_model_changed_fn is not None:
            self._variant_tree_model.remove_item_changed_fn(self._variant_tree_model_changed_fn)
            self._variant_tree_model_changed_fn = None

        # Clear variant tree model
        if self._variant_tree_model:
            self._variant_tree_model.clear()

        self._stage = None
        self._layer_event_sub = None

    def _on_stage_event(self, evt):
        if evt.type == int(omni.usd.StageEventType.OPENED):
            self._on_stage_opened()
        elif evt.type == int(omni.usd.StageEventType.CLOSING):
            self._on_stage_closed()

    # This will be deprecated once we update to a later Kit SDK where omni.kit.usd.layers is updated to use Events 2.0
    def _on_layer_events(self, event: carb.events.IEvent):
        # Handle USD layer switching
        payload = layers.get_layer_event_payload(event)
        if not payload:
            return

        if payload.event_type == layers.LayerEventType.EDIT_TARGET_CHANGED:
            self._on_layer_edit_target_changed(event)

    def _on_layer_edit_target_changed(self, _):
        # If current authoring layer changed, re-populate variant lists
        self._variant_tree_model.clear()
        if self._editor_core._stage.GetPrimAtPath(self._editor_core._get_root_prim_path()).IsValid():
            self._variant_tree_model._populate_variant_set_list()

        self._update_guide_label()

    # Show the UI window. Create one if none exists.
    def show(self):
        if self._options_menu is None:
            self._create_options_menu()
        if self._window is None:
            self._create_window()
        self._window.visible = True

    # Hide the UI Window
    def hide(self):
        if self._window is not None:
            self._window.visible = False

    # Add self to Tools/Variants/Variant Editor
    def _create_menu_entry(self):
        self._menu_entry_items.append(
            MenuItemDescription(
                name=ui_c.PATH_MENU_ENTRY,
                ticked=True,
                ticked_fn=self._is_visible,
                onclick_fn=self._menu_window_toggle,
            )
        )
        self._menu_root = [MenuItemDescription(name="Variants", sub_menu=self._menu_entry_items)]
        menu_utils.add_menu_items(self._menu_root, "Tools")

    # Utility method to query window visibility
    def _is_visible(self) -> bool:
        return False if self._window is None else self._window.visible

    # Toggle the UI window from the menu button
    def _menu_window_toggle(self):
        if self._is_visible():
            self.hide()
        else:
            self.show()

    # Called with the UI window's visibility changes
    def _on_window_visibility_changed(self, visible):
        self._editor_core.authoring_variant = 0

        # If the window was closed
        if visible:
            self._reset_to_defaults()

            StageChangeHelper.enable()
        else:
            # Refresh the "Tools" menu so the tick gets updated
            menu_utils.refresh_menu_items("Tools")
            if not self._closed_via_button:
                self._closed_via_button = False

            self._editor_core._clear_all()
            self._variant_tree_model.clear()

            StageChangeHelper.disable()

    # Create the UI Window for the first time

    def _create_window(self):
        self._window = ui.Window(
            ui_c.PATH_NAME_TOOL,
            visible=False,
            width=ui_c.WINDOW_WIDTH,
            height=ui_c.WINDOW_HEIGHT,
        )

        # Populate window with content
        with self._window.frame:
            self._window_content = ui.VStack(style=ui_c.WINDOW_STYLE)
            with self._window_content:
                # Create and style the actual interface
                self._create_tool_interface()

        self._window.set_visibility_changed_fn(self._on_window_visibility_changed)

    # Add a new variant set using the next available name based on default variant set name
    def _add_variant_set(self):
        if self._variant_tree_model is not None:
            vset = self._variant_tree_model.add_variant_set()
            self._update_guide_label()
            return vset
        else:
            return None

    # Same as previous function, except automatically add one variant
    def _add_new_variant_set(self):
        if self._variant_tree_model is not None:
            with omni.kit.undo.group():
                vset = self._variant_tree_model.add_variant_set()
                cards = self._variant_tree_model.get_item_children()
                for card in cards:
                    if card.data.name == vset:
                        self._variant_tree_model.add_variant(card)
                self._update_guide_label()

    def show_options_menu(self):
        self._options_menu.show()

    # Change the text of the guide label to help the user understand what to do next based on what is present in the editor
    def _update_guide_label(self, active_variant=None, prev_variant_path=None):
        if not self._is_visible():
            return

        if self._prim_list_screen:
            if self._editor_core.active_variant is None:
                # If no variant is selected
                self._prim_list_screen.visible = True
            else:
                # If there is variant selected, then check if it's authored in current layer
                vs_name, v_name = Sdf.Path(self._editor_core.active_variant).GetVariantSelection()

                v_spec = self._editor_core._find_variant_spec(
                    *Sdf.Path(self._editor_core.active_variant).GetVariantSelection()
                )
                if v_spec is None:
                    self._prim_list_screen.visible = True
                else:
                    self._prim_list_screen.visible = False

        if self._guide_label:
            if self._editor_core._stage.GetPrimAtPath(self._editor_core._get_root_prim_path()).IsValid():
                if self._editor_core._collect_variant_sets():
                    if self._editor_core._active_variant:
                        vspecs = []
                        layer_stack = self._editor_core._stage.GetLayerStack()
                        for layer in layer_stack:
                            vspec = layer.GetObjectAtPath(Sdf.Path(self._editor_core.active_variant))
                            if isinstance(vspec, Sdf.VariantSpec):
                                vspecs.append(vspec)
                            else:
                                vspec = None
                        if len(vspecs) == 1:
                            vspec = vspecs[0]

                        if vspec:
                            if vspec.layer != self._editor_core._get_edit_target_layer():
                                self._guide_label.alignment = ui.Alignment.LEFT_CENTER
                                self._guide_label.text = f"{vspec.owner.name} was authored in a different layer: {vspec.layer.GetDisplayName()}\nPlease open that file or change the authoring layer to edit this variant directly.\n"

                    else:
                        self._guide_label.alignment = ui.Alignment.CENTER
                        self._guide_label.text = ui_c.GUIDE_TEXT_NO_SELECTION
                else:
                    self._guide_label.alignment = ui.Alignment.LEFT_CENTER
                    self._guide_label.text = ui_c.GUIDE_TEXT_NO_SETS
            else:
                self._guide_label.alignment = ui.Alignment.LEFT_CENTER
                self._guide_label.text = ui_c.GUIDE_TEXT_NO_PRIM

    def _get_target_prim_path(self):
        if self._editor_core:
            return self._editor_core._target_prim_path
        return None

    # Selecting a new target prim should repopulate the whole window to display information relevant to that prim
    def _on_prim_picked(self, paths: list[str]):
        self._editor_core._update_context_and_stage()
        self._editor_core._clear_all()
        self._variant_tree_model.clear()

        self._editor_core._update_root_prim_path(paths[0])
        if self._variant_set_path_field is not None:
            self._variant_set_path_field.model.set_value(paths[0])
            self._variant_set_path_field.set_tooltip_fn(
                lambda: self._create_tooltip(self._variant_set_path_field.model.as_string)
            )

        self._variant_tree_model._populate_variant_set_list()
        self._update_guide_label()

    # Should the need arise, reload everything
    def _reset_to_defaults(self):
        selection: list[str] = self._editor_core._usd_context.get_selection().get_selected_prim_paths()
        if len(selection) > 0:
            self._editor_core._update_root_prim_path(selection[0])
        else:
            # Get the default prim path
            default_prim = self._editor_core._stage.GetDefaultPrim()

            if default_prim.IsValid():
                default_prim_path = default_prim.GetPath().pathString
                self._editor_core._update_root_prim_path(default_prim_path)
            else:
                self._editor_core._update_root_prim_path(e_c.DEFAULT_ROOT_PRIM_PATH)

        if self._variant_set_path_field:
            self._variant_set_path_field.model.set_value(self._editor_core._get_root_prim_path().pathString)
            self._variant_set_path_field.set_tooltip_fn(
                lambda: self._create_tooltip(self._variant_set_path_field.model.as_string)
            )

        if self._editor_core._stage.GetPrimAtPath(self._editor_core._get_root_prim_path()).IsValid():
            self._variant_tree_model._populate_variant_set_list()

        self._update_guide_label()

    # ===================== Build UI Elements ===========================

    def _create_tool_interface(self):
        with ui.Frame(style={"margin": 0}):
            with ui.ZStack():
                ui.Spacer(width=850)  # Invisible spacer for min window width
                ui.Spacer(height=500)  # Invisible spacer for min window height

                # Stack Major Window Elements Vertically
                with ui.VStack(spacing=4):

                    # ====== Top Row ======
                    # Variant Set Prim Location Label, Field, Prim Picker Button
                    with ui.HStack(skip_draw_when_clipped=False, height=25):
                        ui.Label(
                            "Variant Set Prim Location",
                            width=0,
                            style=ui_c.STYLE_TEXT_LABEL,
                        )
                        ui.Spacer(width=5)
                        with ui.ZStack():
                            with ui.HStack():
                                self._variant_set_path_field = ui.StringField(style=ui_c.STYLE_STRING_FIELD)
                                self._variant_set_path_field.set_accept_drop_fn(self._on_accept_drop)
                                self._variant_set_path_field.set_drop_fn(self._on_drop)
                                self._variant_set_path_field.set_tooltip_fn(
                                    lambda: self._create_tooltip(self._variant_set_path_field.model.as_string)
                                )
                                self._variant_set_path_field.model.add_begin_edit_fn(self._on_field_begin_edit)
                                self._variant_set_path_field.model.add_end_edit_fn(self._on_field_end_edit)
                            with ui.HStack():
                                ui.Spacer()
                                # Z Stack so we can turn on content clipping so the cursor doesn't affect the StringField behind
                                with ui.ZStack(width=26, content_clipping=True):
                                    ui.Rectangle(style={"background_color": ui_c.DarkColors.Background})
                                    self._picker_button = StageWindowButton(
                                        label="",
                                        on_select_fn=self._on_prim_picked,
                                        tooltip_fn=lambda: self._create_tooltip(ui_c.TOOLTIP_SELECT_PRIM),
                                        style=ui_c.STYLE_PICK_PRIM_BUTTON,
                                        targets_limit=1,
                                        width=26,
                                    )
                        ui.Spacer(width=5)
                        ui.Button(
                            width=24,
                            style=ui_c.STYLE_MENU_BUTTON,
                            tooltip_fn=lambda: self._create_tooltip(ui_c.TOOLTIP_BUTTON_VARIANT_OPTIONS),
                            clicked_fn=self.show_options_menu,
                        )

                    # ====== Middle Section ======
                    # Left Column (Variant Set List), Right Column (Prim List/Properties)
                    with ui.HStack(
                        spacing=4,
                        style={
                            "border_radius": 2,
                            "background_color": ui_c.COLORS.CLR_1,
                        },
                    ):

                        # ====== Left Column ======
                        with ui.ZStack(width=ui.Percent(30)):
                            # ui.Spacer(width=250)  # Invisible spacer for min window width, specific to this column/frame
                            ui.Rectangle()  # Column background

                            # Vertical Stack for left column
                            # Add Variant Set Button on top of list view/scrolling frame
                            with ui.VStack(style={"margin": 2}):
                                with ui.ZStack(height=40):
                                    # Add Variant Set Button
                                    self._add_variant_set_button = ui.Button(
                                        "Add New Variant Set",
                                        style=ui_c.STYLE_BUTTON,
                                        tooltip_fn=lambda: self._create_tooltip(ui_c.TOOLTIP_BUTTON_ADD_VARIANT_SET),
                                        clicked_fn=self._add_new_variant_set,
                                    )
                                    # Add Variant Set Button '+' icon (centered and positioned)
                                    with ui.HStack():
                                        ui.Spacer(width=ui.Percent(15))  # '+' position offset
                                        with ui.VStack(width=0):
                                            ui.Spacer()
                                            ui.Image(
                                                f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_ADD_DARK}",
                                                width=20,
                                                height=20,
                                                style=ui_c.STYLE_ICON_NO_HOVER,
                                            )
                                            ui.Spacer()
                                        ui.Spacer()

                                with ui.ZStack(style={"margin": 0}):
                                    # Tree View
                                    self._variant_tree_view = VariantTreeView(
                                        model=self._variant_tree_model,
                                        delegate=self._variant_tree_delegate,
                                    )
                                    self._variant_tree_model._tree = weakref.ref(self._variant_tree_view._tree_view)

                        # ====== Right Column ======
                        with ui.ZStack():
                            # ui.Spacer(width=600)  # Invisible spacer for min window width, specific to this column/frame
                            ui.Rectangle()  # Column background

                            # Add Prim Button on top of prim view/scrolling frame
                            with ui.VStack(style={"margin": 2}):
                                with ui.ZStack(height=40):
                                    # Add Prim Button
                                    self._picker_button = StageWindowButton(
                                        filter_by_text=False,
                                        label="Add Prim",
                                        on_select_fn=self._variant_tree_model.ensure_add_prims_to_variant,
                                        tooltip_fn=lambda: self._create_tooltip(ui_c.TOOLTIP_SELECT_PRIM),
                                        style=ui_c.STYLE_BUTTON,
                                        targets_limit=1000,
                                        width=ui.Percent(100),
                                        fn_target_path=self._get_target_prim_path,
                                    )

                                    # Add Prim Button '+' icon (centered and positioned)
                                    with ui.HStack():
                                        ui.Spacer(width=ui.Percent(40))
                                        with ui.VStack(width=0):
                                            ui.Spacer()
                                            ui.Image(
                                                f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_ADD_DARK}",
                                                width=20,
                                                height=20,
                                                style=ui_c.STYLE_ICON_NO_HOVER,
                                            )
                                            ui.Spacer()
                                        ui.Spacer()

                                # Vertical Stack for right column
                                # Prim List
                                self._prim_property_tree_view = PrimPropertyView(
                                    model=self._variant_tree_model,
                                    delegate=self._prim_property_tree_delegate,
                                )

                            # Screen that prompts the user to select a variant
                            self._prim_list_screen = ui.ZStack()
                            with self._prim_list_screen:
                                ui.Rectangle()
                                with ui.VStack():
                                    ui.Spacer()
                                    with ui.HStack():
                                        ui.Spacer()
                                        self._guide_label = ui.Label(
                                            ui_c.GUIDE_TEXT_NO_PRIM,
                                            width=350,
                                            alignment=ui.Alignment.CENTER,
                                            style=ui_c.STYLE_TEXT_LABEL,
                                            word_wrap=True,
                                        )
                                        ui.Spacer()
                                    ui.Spacer()

    def _create_options_menu(self):
        self._options_menu = ui.Menu("Options", menu_compatibility=False, tearable=False)
        with self._options_menu:
            # ui.MenuItem("Options", enabled=False)
            # ui.Separator()
            ui.MenuItem(
                ui_c.ADD_PROP_TO_ALL_VARIANTS_TEXT,
                checkable=True,
                checked=VariantEditorCore().add_props_to_all_variants,
                checked_changed_fn=self._on_add_props_to_all_variants,
            )
            ui.MenuItem(
                ui_c.CREATE_VISIBILITY_BY_DEFAULT_TEXT,
                checkable=True,
                checked=VariantEditorCore().create_visibility_by_default,
                checked_changed_fn=self._on_create_visibility_by_default,
            )

    # Tooltip helper function
    def _create_tooltip(self, text: str):
        with ui.ZStack(style=ui_c.STYLE_TOOLTIP):
            ui.Rectangle()
            ui.Label(text, style=ui_c.STYLE_TOOLTIP_TEXT)

    # =================== Assign callbacks to UI elements =============

    def _on_add_props_to_all_variants(self, value):
        self._editor_core.add_props_to_all_variants = value

    def _on_create_visibility_by_default(self, value):
        self._editor_core.create_visibility_by_default = value

    # Drag and drop for Main Target Prim - Can accept just about anything
    def _on_accept_drop(self, item):
        prim = self._editor_core._stage.GetPrimAtPath(item)
        if prim.IsValid():
            return True

    # Once dropped, update main target prim
    def _on_drop(self, item):
        path_list = item.mime_data.split("\n")
        self._on_prim_picked(path_list)

    # Begin edit of the Variant Set Path StringField
    def _on_field_begin_edit(self, id):
        self._stringfield_value = self._variant_set_path_field.model.as_string

    # End edit of the Variant Set Path StringField
    # Returns the stringfield to the previous string value if the one entered is invalid
    def _on_field_end_edit(self, id):
        prim = self._editor_core._stage.GetPrimAtPath(self._variant_set_path_field.model.as_string)
        if not prim.IsValid():
            if self._stringfield_value is not None:
                nm.post_notification(
                    f"{self._variant_set_path_field.model.as_string} is an invalid path.\nResetting path to: {self._stringfield_value}",
                    status=nm.NotificationStatus.WARNING,
                )
                self._variant_set_path_field.model.set_value(self._stringfield_value)
            else:
                carb.log_warn(f"{self._variant_set_path_field.model.as_string} is an invalid path.")
        else:
            self._on_prim_picked([self._variant_set_path_field.model.as_string])

    # ================== UI Element Update Functions =====================
    def set_tree_view_expanded(self, model: VariantTreeModel, item):
        if self._variant_tree_view is None or self._prim_property_tree_view is None:
            return

        # Expand tree view items
        if item is None:
            self._variant_tree_view._tree_view.set_expanded(None, True, False)
            self._prim_property_tree_view._tree_view.set_expanded(None, True, False)

        elif isinstance(item, VariantSetCardItem):
            # Expand variant set branch when it's updated
            if not self._variant_tree_view._tree_view.is_expanded(item):
                self._variant_tree_view._tree_view.set_expanded(
                    item, expanded=model.get_expanded(item.data.name), recursive=True
                )

            if not self._prim_property_tree_view._tree_view.is_expanded(item):
                self._prim_property_tree_view._tree_view.set_expanded(item, expanded=True, recursive=True)

        elif isinstance(item, VariantCardItem):
            # Prim item gets added
            vset_item = model.get_parent_item(item)

            if not self._prim_property_tree_view._tree_view.is_expanded(vset_item):
                self._prim_property_tree_view._tree_view.set_expanded(vset_item, expanded=True, recursive=False)

            if not self._prim_property_tree_view._tree_view.is_expanded(item):
                self._prim_property_tree_view._tree_view.set_expanded(item, expanded=True, recursive=False)

        elif isinstance(item, PrimCardItem):
            # Property item got added
            variant_item = model.get_parent_item(item)
            vset_item = model.get_parent_item(variant_item)

            if not self._prim_property_tree_view._tree_view.is_expanded(vset_item):
                self._prim_property_tree_view._tree_view.set_expanded(vset_item, expanded=True, recursive=True)

            if not self._prim_property_tree_view._tree_view.is_expanded(variant_item):
                self._prim_property_tree_view._tree_view.set_expanded(variant_item, expanded=True, recursive=True)

            if not self._prim_property_tree_view._tree_view.is_expanded(item):
                # TODO: get rid of this selection trick is only used to expand the prim card
                self._prim_property_tree_view._tree_view.selection
                self._prim_property_tree_view._tree_view.set_expanded(item, expanded=True, recursive=False)

    def is_changed_path_needed(self, path: Sdf.Path):
        root_item_path = self._editor_core._get_root_prim_path()
        return path.HasPrefix(root_item_path) or root_item_path.HasPrefix(path)

    def on_stage_changed(self):
        if not self._editor_core:
            return

        stage = self._editor_core._stage

        if not stage:
            return

        root_item_path = self._editor_core._get_root_prim_path()

        if self.is_stage_obj_changed(root_item_path):
            root_prim = stage.GetPrimAtPath(root_item_path)
            if not root_prim or not root_prim.IsActive():
                self._on_root_prim_removed()
            else:
                self._on_root_prim_changed()
                self._variant_tree_model._populate_variant_set_list()
        elif root_item_path in self.changed_paths:
            # When a variant is removed or added, a info only change notice is triggered without any info tokens.
            infos = self.changed_paths[root_item_path]
            if infos is not None and not infos:
                self._variant_tree_model._populate_variant_set_list()

        paths_to_remove = {}
        for path in self.changed_paths:
            if self._editor_core.is_prim_path_in_metadata(path):
                all_valid_metadata_paths = self._editor_core.is_prim_path_in_metadata(path)
                for key in all_valid_metadata_paths.keys():
                    if not stage.GetPrimAtPath(path):
                        value = all_valid_metadata_paths[key]
                        paths_to_remove[key.path] = value
        if len(paths_to_remove) > 0:
            for path_and_stem in paths_to_remove.items():
                variant_path = path_and_stem[0]
                value = path_and_stem[1]
                self._editor_core._remove_prim_path_from_metadata(variant_path, value)
            self._variant_tree_model._populate_variant_set_list()

    def _on_root_prim_changed(self):
        self._update_guide_label()

    def _on_root_prim_removed(self):
        self._variant_tree_model.clear()
        self._reset_to_defaults()

    # ================== Entry Points for other UIs ======================

    # Add self to stage context window "Edit Variants"

    def __connect_stage_window(self):
        path = omni.usd.get_context().get_selection().get_selected_prim_paths()
        stage_context_menu = {
            "name": "Edit Variants",
            "glyph": "menu_rename.svg",
            "onclick_fn": self._open_from_stage_context,
            "show_fn": lambda arg: self.__stage_selection_supported(arg),
        }
        self._stage_context_menu_sub = cm.add_menu(stage_context_menu, "MENU", "omni.kit.widget.stage")

    # Disconnect from stage window on cleanup
    def __disconnect_stage_window(self):
        if self._stage_context_menu_sub:
            self._stage_context_menu_sub.release()
            self._stage_context_menu_sub = None

    # Connect to content browser context menu "Create Variant Set"
    def __connect_content_browser(self):
        import omni.kit.window.content_browser

        self._content_browser = omni.kit.window.content_browser.get_content_window()
        self._content_browser.add_context_menu(
            "Create Variant Set",
            glyph="menu_add.svg",
            click_fn=self.__create_variants_from_content,
            show_fn=self.__is_asset_supported,
        )

    # Disconnect from Content Browser on cleanup
    def __disconnect_content_browser(self):
        if self._content_browser:
            self._content_browser.delete_context_menu("Create Variant Set")

    # Connect to Property Window "Add" button.  Automatically puts a hook into Stage Context Menu under "Add"
    def __connect_property_window(self):
        import omni.kit.property.usd
        from omni.kit.property.usd import PrimPathWidget

        context_menu = cm.get_instance()
        if context_menu is None:
            self._menu_button1 = None
            self._menu_button2 = None
            carb.log_error("context_menu is disabled!")
            return None

        self._create_variant_btn = PrimPathWidget.add_button_menu_entry(
            "Variant Set",
            show_fn=lambda payload: self.__property_selection_supported(payload),
            onclick_fn=lambda payload: self.__create_variant_set_from_property(payload),
        )

        # Create the Context menu entries
        menu_dict = {
            "name": "Variants",
            "populate_fn": self._populate_context_variants,
        }
        self._variants_context_menu = cm.add_menu(menu_dict, "MENU", "omni.kit.window.viewport")

    # Disconnect from Property Window on cleanup
    def __disconnect_property_window(self):
        if self._create_variant_btn:
            from omni.kit.property.usd import PrimPathWidget

            PrimPathWidget.remove_button_menu_entry(self._create_variant_btn)
            self._create_variant_btn = None

        if self._variants_context_menu:
            self._variants_context_menu = None

    def _populate_context_variants(self, objects):
        if "prim_list" in objects:
            prims = objects["prim_list"]
            num_prims = len(objects["prim_list"])
            for prim in prims:
                if prim.HasVariantSets():
                    prim_name = prim.GetName()
                    vset_names = prim.GetVariantSets().GetNames()
                    # Display the name of the prim whose variants we are showing if the # of selected prims is > 1
                    if num_prims > 1:
                        with ui.HStack():
                            ui.Spacer(width=6)
                            ui.Label(
                                prim_name,
                                elided_text=True,
                                style={"color": ui_c.COLORS.CLR_7},
                                tooltip_fn=lambda: self._create_tooltip(prim_name),
                            )
                    for name in vset_names:
                        vset = prim.GetVariantSet(name)
                        cur_sel = vset.GetVariantSelection()
                        variants = vset.GetVariantNames()

                        # keep copy objects to prevent python GC
                        populate_name = "populate_variant_" + name
                        objects[populate_name] = {}
                        objects[populate_name]["populate_menu"] = cm.ContextMenuExtension.uiMenu(
                            name, submenu=True, tearable=True
                        )
                        objects[populate_name]["populate_menus"] = []
                        objects[populate_name]["populate_submenus"] = []
                        with objects[populate_name]["populate_menu"]:
                            for variant in variants:
                                objects[populate_name]["populate_menus"].append(
                                    cm.ContextMenuExtension.uiMenu(direction=ui.Direction.LEFT_TO_RIGHT)
                                )
                                with objects[populate_name]["populate_menus"][-1]:
                                    # If there's a current variant selection...
                                    if cur_sel != "":
                                        # If the current variant is the selection, style appropriately
                                        if variant == cur_sel:
                                            ui.Spacer(width=5)
                                            ui.Rectangle(
                                                width=4,
                                                style={
                                                    "border_radius": 1,
                                                    "background_color": ui_c.COLORS.CLR_LIGHT_BLUE,
                                                },
                                            )
                                            objects[populate_name]["populate_submenus"].append(
                                                cm.ContextMenuExtension.uiMenuItem(
                                                    variant,
                                                    style={"color": ui_c.COLORS.CLR_LIGHT_BLUE},
                                                    triggered_fn=lambda *_, vset_arg=vset, variant_arg=variant: self._variant_clicked(
                                                        vset_arg, variant_arg
                                                    ),
                                                )
                                            )
                                        # If this variant is not the selection, add a margin to match the selected variant's margin
                                        else:
                                            ui.Spacer(width=9)
                                            objects[populate_name]["populate_submenus"].append(
                                                cm.ContextMenuExtension.uiMenuItem(
                                                    variant,
                                                    triggered_fn=lambda *_, vset_arg=vset, variant_arg=variant: self._variant_clicked(
                                                        vset_arg, variant_arg
                                                    ),
                                                )
                                            )
                                    # If there's no variant selection, left-align all entries w/o a margin
                                    else:
                                        objects[populate_name]["populate_submenus"].append(
                                            cm.ContextMenuExtension.uiMenuItem(
                                                variant,
                                                triggered_fn=lambda *_, vset_arg=vset, variant_arg=variant: self._variant_clicked(
                                                    vset_arg, variant_arg
                                                ),
                                            )
                                        )
                    break

    def _variant_clicked(self, vset, vname):
        cur_sel = vset.GetVariantSelection()
        if cur_sel == vname:
            self._editor_core._select_variant(vset, "")
        else:
            self._editor_core._select_variant(vset, vname)

    # Content Browser will present "Create Variant" button with most selection sets.
    # It just currently only knows what to do with MDLs and USD(x) files.
    def __is_asset_supported(self, asset):
        import omni.kit.window.content_browser

        contentBrowser = omni.kit.window.content_browser.get_content_window()
        selections = []
        selections = contentBrowser.get_current_selections(pane=2)
        supported = False
        if selections is not None:
            if asset not in selections:
                selections.append(asset)
            for item in selections:
                # OM-98804: Only create variant set on usd and mdl files in Content browser
                if item.endswith(".usd") or item.endswith(".usda") or item.endswith(".usdc") or item.endswith(".usdz"):
                    supported = True
                elif item.endswith(".mdl"):
                    supported = True
        return supported

    # Property Window and Stage Context "Add" menu will only present "Add/Variant Set" if you have exactly one prim selected
    def __property_selection_supported(self, payload):
        paths = payload.get("prim_list")
        if paths:
            if len(paths) == 1:
                return True
            else:
                return False
        else:
            return False

    # Stage Context Menu "Edit Variants" button will only present if you have exactly one prim selected
    def __stage_selection_supported(self, payload):
        paths = payload.get("prim_list")
        if paths:
            if len(paths) == 1:
                return True
            else:
                return False
        else:
            return False

    # When opening from stage context, get the selected prim and set it to the root prim path
    def _open_from_stage_context(self, payload):
        paths = payload.get("prim_list")
        self.show()
        path = paths[0].GetPath().pathString

        self._on_prim_picked([path])

    # When creating a variant set from the content browser, open the window and then prompt the user
    # to select the root prim for their new variant set
    def __create_variants_from_content(self, button, asset):
        self.show()
        self._select_root_prim()

    # Root Prim Selection Dialog
    def _select_root_prim(self):
        RootSelector(
            filter_type_list=[],
            on_select_fn=self._create_variants_from_files,
            targets_limit=1,
        )

    # Based on whatever files you selected, set up the new variant set to
    # either set up material binding relationships or references/payloads based on drag and drop import settings
    def _create_variants_from_files(self, paths):
        self._on_prim_picked(paths)
        content_browser = omni.kit.window.content_browser.get_content_window()
        selections = content_browser.get_current_selections(pane=2)
        vset_name = self._add_variant_set()
        payload_setting = carb.settings.get_settings().get("/persistent/app/stage/dragDropImport")
        usd_list = []
        mdl_list = []
        for item in selections:
            if item.endswith(".usd") or item.endswith(".usda") or item.endswith(".usdc") or item.endswith(".usdz"):
                usd_list.append(item)
            elif item.endswith(".mdl"):
                mdl_list.append(item)

        if self._editor_core.create_visibility_by_default:
            self._editor_core._create_visibility_variant_from_files(vset_name, usd_list, payload_setting)
        else:
            self._editor_core._create_geom_variant_from_files(vset_name, usd_list, payload_setting)
        self._editor_core._create_material_variant_from_files(vset_name, mdl_list)

    # When creating a new variant set from the property panel or stage context "add" menu
    # Open the editor, set the main prim path, and create a new variant set.
    def __create_variant_set_from_property(self, payload):
        self.show()
        payload_path = [payload.get_paths()[0].pathString]
        self._on_prim_picked(payload_path)
        self._add_variant_set()

    # duplicate variant action callback for the hotkey
    def duplicate_variant_action(self):
        if self._variant_tree_model is None:
            return
        variant_card = self._variant_tree_model.get_active_variant_card_item_by_path(self._editor_core.active_variant)
        if variant_card:
            self._variant_tree_model.duplicate_variant(variant_card)

    # rename variant action callback for the hotkey
    def rename_variant_action(self):
        if self._variant_tree_model is None:
            return
        variant_card = self._variant_tree_model.get_active_variant_card_item_by_path(self._editor_core.active_variant)
        if variant_card:
            variant_card._ui_widget.call_mouse_double_clicked_fn(0, 0, 0, 0)
