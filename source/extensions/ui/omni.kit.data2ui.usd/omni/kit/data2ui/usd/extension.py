# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import os
from functools import partial
from pathlib import Path

import carb.eventdispatcher
import carb.settings
import carb.tokens
import omni.ext
import omni.kit.actions.core
import omni.kit.app
import omni.kit.commands
import omni.kit.viewport.utility
import omni.ui as ui
import omni.usd

from ..core import DDView, OmniUiDelegate
from .actions.create_actions import deregister_actions, register_actions
from .commands.create_commands import deregister_commands, register_commands
from .model import Model as UsdModel
from .prims import PRIM_NS, valid_ui_prim_categories, valid_ui_prim_types
from .prims.prim_style_properties import prims_add_style_property, prims_allows_style_property
from .properties.prim_properties import ATTR_NS, DISABLED_PROPERTY, all_prim_style_properties

_extension_instance = None
_extension_path = None

PERSISTENT_SETTINGS_PREFIX = "/persistent"
ICON_PATH = Path(__file__).parent.parent.parent.parent.parent.joinpath("icons")
VIEWPORT_FRAME = "Data Driven Viewport Frame"


class Data2UIUSDExtension(omni.ext.IExt):
    """
    The Data2UI USD Extension class
    """

    def on_startup(self, ext_id):
        global _extension_instance
        _extension_instance = self

        global _extension_path
        _extension_path = omni.kit.app.get_app_interface().get_extension_manager().get_extension_path(ext_id)

        self._ext_name = omni.ext.get_extension_name(ext_id)

        self._frame = None
        self._delegate = None
        self._model = None
        self._view = None
        self._window_view = None
        self._window = None
        self._viewport_view = None

        self._create_data2ui_menu_categories_lists = None
        self._create_data2ui_menu_list = None
        self._create_data2ui_menu = []
        self._data2ui_contextmenu = None
        self._add_data2ui_contextmenu = None
        self._data2ui_style_menu = None
        self._reorder_data2ui_contextmenu = None
        self._frame_view_data2ui_contextmenu = None
        self._stage_contextmenus = []
        self._data2ui_reorder_menu = None
        self._reorder_data2ui_contextmenu_items = []
        self._data2ui_frame_view_menu = None
        self._registered_widget = False
        self._create_data2ui_contextmenu = None
        self._create_data2ui_contextmenu_list = None
        self._create_data2ui_contextmenu_category_entries = None
        self._event_unloader = None
        self._event_unloaders = []
        self._usd_context = None

        # Register these before building the menus because the context menu uses the actions
        register_commands()
        register_actions(self._ext_name, Data2UIUSDExtension, lambda: _extension_instance)
        self._register_event_unloaders()
        if carb.settings.get_settings().get_as_bool("/exts/omni.no_code_ui.authoring/enabled"):
            self._register_stage_icons()
            self._register_property_widget()
            from omni.kit.context_menu import get_instance as get_context_menu_instance

            self._context_menu = get_context_menu_instance()

            self._register_add_property_menu()
            self._register_reorder_prim_menu()
            self._register_frame_view_menus()
            self._register_stage_context_menus()

            self._build_create_data2ui_menu()
            self._register_disable_attribute()

    def on_shutdown(self):

        global _extension_instance

        self._unregister_stage_context_menus()
        self._unregister_frame_view_menus()
        self._unregister_reorder_prim_menu()
        self._unregister_add_property_menu()
        self._context_menu = None
        if self._registered_widget:
            self._unregister_property_widget()
        deregister_actions(self._ext_name)
        deregister_commands()
        _extension_instance = None

        self._usd_context = None
        self._event_unloader = None
        for observer in self._event_unloaders:
            observer.reset()
        self._event_unloaders.clear()
        self._reorder_data2ui_contextmenu = None
        self._frame_view_data2ui_contextmenu = None
        self._data2ui_contextmenu = None
        try:
            from omni.kit.menu.utils import remove_menu_items

            remove_menu_items(self._create_data2ui_menu, "Create")
        except ModuleNotFoundError:
            pass
        self._data2ui_contextmenu = None
        self._create_data2ui_contextmenu = None
        self._create_data2ui_contextmenu_list = None
        self._create_data2ui_contextmenu_category_entries = None
        self._create_data2ui_menu = []
        self._create_data2ui_menu_list = None

        self._frame = None
        self._delegate = None
        self._model = None
        self._view = None
        self._window = None
        self._window_view = None
        self._viewport_view = None

    @staticmethod
    def _execute_action_for_contextmenu(objects: dict, action_name: str):
        action_registry = omni.kit.actions.core.get_action_registry()
        action = action_registry.get_action("omni.kit.data2ui.usd", action_name)
        action.execute()

    @staticmethod
    def _execute_reorder_for_contextmenu(objects: dict, action_name: str):
        action_registry = omni.kit.actions.core.get_action_registry()
        action = action_registry.get_action("omni.kit.data2ui.usd", action_name)
        action.execute()

    def _execute_view(self, frame_prim, view_type: str):
        self._model = UsdModel(frame_prim)
        self._delegate = OmniUiDelegate()

        if view_type.lower() == "window":
            self._window = ui.Window(
                "Data Driven", width=200, height=200
            )  # Where do we want to pull title/width/height from?
            with self._window.frame:
                self._window_view = DDView(model=self._model, delegate=self._delegate)

        elif view_type.lower() == "frame":
            self._frame = ui.Frame()
            with self._frame:
                self._view = DDView(model=self._model, delegate=self._delegate)

        elif view_type.lower() == "viewport":
            if avw := omni.kit.viewport.utility.get_active_viewport_window(window_name="Viewport"):
                if self._viewport_view is not None:
                    self._viewport_view.destroy()

                self._frame = avw.get_frame(VIEWPORT_FRAME)
                with self._frame:
                    self._viewport_view = DDView(model=self._model, delegate=self._delegate)  # , usd=True)

        elif view_type.lower() == "remove viewport":
            if avw := omni.kit.viewport.utility.get_active_viewport_window(window_name="Viewport"):
                if self._view is not None:
                    self._view.destroy()
                if self._viewport_view is not None:
                    self._viewport_view.destroy()
                self._frame = avw.get_frame(VIEWPORT_FRAME)
                self._frame.clear()

    def _shutdown_views(self):
        # Kill the views first
        self._view = None
        self._window_view = None
        self._viewport_view = None
        # Kill any frames, then any windows
        if self._window:
            if self._window.frame:
                self._window.frame.clear()
        if self._frame:
            self._frame.clear()

        self._window = None
        self._frame = None
        # Finally kill the delegate and model
        self._delegate = None
        self._model = None

    def _execute_view_for_contextmenu(self, objects: dict, view_type: str):
        _frame_prim = objects.get("hovered_prim", None)
        if not _frame_prim:
            return
        self._execute_view(_frame_prim, view_type)

    def _build_create_data2ui_menu(self):
        from omni.kit.context_menu import add_menu
        from omni.kit.menu.utils import MenuItemDescription, add_menu_items

        # setup menus
        self._create_data2ui_menu = []
        self._create_data2ui_contextmenu = []
        self._create_data2ui_menu_list = []
        self._create_data2ui_contextmenu_list = []
        self._create_data2ui_menu_category_entries = {}
        self._create_data2ui_contextmenu_category_entries = {}

        for idx, category in enumerate(valid_ui_prim_categories):
            self._create_data2ui_menu_category_entries[category] = []
            self._create_data2ui_contextmenu_category_entries[category] = []
            prim_types = valid_ui_prim_categories.get(category, [])

            self._create_data2ui_menu_list.append(MenuItemDescription(header=category))

            self._create_data2ui_contextmenu_list.append(
                {
                    "header": category,
                }
            )

            for prim_type in prim_types:
                glyph_name = "frame.svg" if prim_type.lower().endswith("frame") else f"{prim_type.lower()}.svg"
                glyph_path = carb.tokens.get_tokens_interface().resolve("${glyphs}/" + glyph_name)
                self._create_data2ui_menu_list.append(
                    MenuItemDescription(
                        name=f"{prim_type}",
                        glyph="" if not os.path.exists(glyph_path) else glyph_name,
                        onclick_action=("omni.kit.data2ui.usd", f"create_ui_prim_{prim_type.lower()}"),
                    )
                )
                pt = prim_type.lower()
                self._create_data2ui_contextmenu_list.append(
                    {
                        "name": f"{prim_type}",
                        "glyph": "" if not os.path.exists(glyph_path) else glyph_name,
                        "show_fn": [],
                        "onclick_fn": lambda objects, prim_type=pt: self._execute_action_for_contextmenu(
                            objects=objects, action_name=f"create_ui_prim_{prim_type}"
                        ),
                    }
                )

        self._create_data2ui_menu_list.append(MenuItemDescription(header="Window"))

        self._create_data2ui_contextmenu_list.append(
            {
                "header": "Window",
            }
        )

        self._create_data2ui_menu_list.append(
            MenuItemDescription(
                name="Viewport Frame",
                # glyph: None
                onclick_action=("omni.kit.data2ui.usd", "create_viewport_ui_frame"),
            )
        )

        self._create_data2ui_contextmenu_list.append(
            {
                "name": "Viewport Frame",
                # "glyph": None,
                "use_hovered": False,
                "show_fn": [],
                "onclick_fn": lambda objects: self._execute_action_for_contextmenu(
                    objects=objects, action_name="create_viewport_ui_frame"
                ),
            }
        )

        self._create_data2ui_menu_list.append(
            MenuItemDescription(
                name="Window Frame",
                # glyph: None
                onclick_action=("omni.kit.data2ui.usd", "create_window_ui_frame"),
            )
        )

        self._create_data2ui_contextmenu_list.append(
            {
                "name": "Window Frame",
                # "glyph": None,
                "use_hovered": False,
                "show_fn": [],
                "onclick_fn": lambda objects: self._execute_action_for_contextmenu(
                    objects=objects, action_name="create_window_ui_frame"
                ),
            }
        )

        self._create_data2ui_menu.append(
            MenuItemDescription(name="UI", glyph="data2ui.svg", sub_menu=self._create_data2ui_menu_list)
        )
        self._create_data2ui_contextmenu = {
            "name": {"UI": self._create_data2ui_contextmenu_list},
            "glyph": "data2ui.svg",
        }

        add_menu_items(self._create_data2ui_menu, "Create", -7)
        self._data2ui_contextmenu = add_menu(self._create_data2ui_contextmenu, "CREATE")

    def _register_property_widget(self):
        import omni.kit.window.property as p

        from .properties.prim_property_widget import Data2UISchemaPropertiesWidget

        w = p.get_window()
        if w:

            w.register_widget(
                "prim",  # Since there isn't any real IsA schema yet, Data2UI widgets will show on all prims for now
                "ui",
                Data2UISchemaPropertiesWidget(
                    "UI",
                    False,
                ),
            )
            self._registered_widget = True

    @staticmethod
    def _prim_add_style_property(objects: dict, property_name: str):
        prim_list = objects.get("prim_list", [])
        prims_add_style_property(None, prim_list, property_name)

    @staticmethod
    def _menu_prim_allows_style_property(objects: dict, property_name: str):
        prim_list = objects.get("prim_list", [])
        return prims_allows_style_property(None, prim_list, property_name)

    @staticmethod
    def _menu_prim_is_frame(objects: dict):
        prim_list = objects.get("prim_list", [])
        if len(prim_list) == 1:
            type_name = prim_list[0].GetTypeName()
            if type_name.startswith(PRIM_NS) and "Frame" in type_name:
                return True
        return False

    @staticmethod
    def _menu_prim_is_ui_prim(objects: dict):
        prim_list = objects.get("prim_list", [])
        for prim in prim_list:
            prim_type_name = prim.GetTypeName()
            if not prim_type_name.startswith(PRIM_NS):
                return False
            if not prim_type_name.split(PRIM_NS)[1] in valid_ui_prim_types:
                return False
        return bool(prim_list)

    @staticmethod
    def _widget_prim_allows_style_property(property_name, objects):
        prim_list = objects.get("prim_list", [])
        stage = objects.get("stage", None)
        return prims_allows_style_property(stage, prim_list, property_name)

    @staticmethod
    def _widget_prim_add_style_property(property_name, payload):
        prim_list = payload.get_paths()
        stage = payload.get_stage()
        prims_add_style_property(stage, prim_list, property_name)

    def _register_add_property_menu(self):
        from omni.kit.context_menu import add_menu
        from omni.kit.property.usd import PrimPathWidget

        if self._context_menu is None:
            self._data2ui_style_menu = None
            return None
        self._data2ui_style_menu = []
        self._add_data2ui_contextmenu_items = []

        for style_property_name in all_prim_style_properties:
            if style_property_name == "custom" or style_property_name == "binding":
                continue
            self._data2ui_style_menu.append(
                PrimPathWidget.add_button_menu_entry(
                    f"UI Property/{style_property_name}",
                    enabled_fn=partial(self._widget_prim_allows_style_property, style_property_name),
                    onclick_fn=partial(self._widget_prim_add_style_property, style_property_name),
                    add_to_context_menu=False,
                )
            )
            self._add_data2ui_contextmenu_items.append(
                {
                    "name": f"{style_property_name}",
                    "enabled_fn": lambda objects, p=style_property_name: self._menu_prim_allows_style_property(
                        objects=objects, property_name=p
                    ),
                    "onclick_fn": lambda objects, p=style_property_name: self._prim_add_style_property(
                        objects=objects, property_name=p
                    ),
                }
            )
        self._data2ui_style_menu.append(
            PrimPathWidget.add_button_menu_entry(  # separators don't seem to work here
                "UI Property/----",
                enabled_fn=lambda *x: None,
                add_to_context_menu=False,
            )
        )
        self._add_data2ui_contextmenu_items.append({})

        self._data2ui_style_menu.append(
            PrimPathWidget.add_button_menu_entry(
                "UI Property/Custom style string",
                enabled_fn=partial(self._widget_prim_allows_style_property, "custom"),
                onclick_fn=partial(self._widget_prim_add_style_property, "custom"),
                add_to_context_menu=False,
            )
        )
        self._add_data2ui_contextmenu_items.append(
            {
                "name": "Custom style string",
                "enabled_fn": lambda objects, p="custom": self._menu_prim_allows_style_property(
                    objects=objects, property_name=p
                ),
                "onclick_fn": lambda objects, p="custom": self._prim_add_style_property(
                    objects=objects, property_name=p
                ),
            }
        )

        self._data2ui_style_menu.append(
            PrimPathWidget.add_button_menu_entry(
                "UI Property/Style Container Binding",
                enabled_fn=partial(self._widget_prim_allows_style_property, "binding"),
                onclick_fn=partial(self._widget_prim_add_style_property, "binding"),
                add_to_context_menu=False,
            )
        )
        self._add_data2ui_contextmenu_items.append(
            {
                "name": "Style Container Binding",
                "enabled_fn": lambda objects, p="binding": self._menu_prim_allows_style_property(
                    objects=objects, property_name=p
                ),
                "onclick_fn": lambda objects, p="binding": self._prim_add_style_property(
                    objects=objects, property_name=p
                ),
            }
        )

        self._add_data2ui_contextmenu_root = {
            "name": {"UI Property": self._add_data2ui_contextmenu_items},
        }
        self._add_data2ui_contextmenu = add_menu(self._add_data2ui_contextmenu_root, "ADD")

    def _unregister_add_property_menu(self):
        # omni.kit.property.usd is optional: import it only when menu entries were registered with it.
        if self._data2ui_style_menu:
            from omni.kit.property.usd import PrimPathWidget

            for button in self._data2ui_style_menu:
                try:
                    PrimPathWidget.remove_button_menu_entry(button)
                except Exception:
                    pass
        self._data2ui_style_menu = None
        self._add_data2ui_contextmenu = None

    def _register_reorder_prim_menu(self):
        if self._context_menu is None:
            self._data2ui_reorder_menu = None
            return None
        self._data2ui_reorder_menu = []
        self._reorder_data2ui_contextmenu_items = []

        self._reorder_data2ui_contextmenu_items.append(
            {
                "header": "UI Commands",
                "name": "UI Commands",
                "enabled_fn": [
                    lambda objects: self._menu_prim_is_ui_prim(objects=objects),
                ],
                "show_fn": self._menu_prim_is_ui_prim,
            }
        )

        for direction in ["Up", "Down"]:
            self._reorder_data2ui_contextmenu_items.append(
                {
                    "name": f"Move Prims {direction}",
                    "enabled_fn": [
                        lambda objects: self._menu_prim_is_ui_prim(objects=objects),
                    ],
                    "glyph": f"arrow_{direction.lower()}.svg",
                    "onclick_fn": lambda objects, direction=direction: self._execute_reorder_for_contextmenu(
                        objects=objects,
                        action_name=f"reorder_ui_prims_{direction.lower()}",
                    ),
                    "show_fn": self._menu_prim_is_ui_prim,
                }
            )

        # self._reorder_data2ui_contextmenu = omni.kit.context_menu.add_menu(self._reorder_data2ui_contextmenu_items, "MENU")

    def _unregister_reorder_prim_menu(self):
        # omni.kit.property.usd is optional: import it only when menu entries were registered with it.
        if self._data2ui_reorder_menu:
            from omni.kit.property.usd import PrimPathWidget

            for button in self._data2ui_reorder_menu:
                PrimPathWidget.remove_button_menu_entry(button)
        self._data2ui_reorder_menu = None
        self._reorder_data2ui_contextmenu_items.clear()

    def _register_frame_view_menus(self):
        if self._context_menu is None:
            self._data2ui_frame_view_menu = None
            return None
        self._data2ui_frame_view_menu = []
        self._data2ui_frame_view_contextmenu_items = []

        for view_type in ["Viewport", "Remove Viewport", "Window", "Frame"]:
            if view_type == "Frame":
                view_label = ""
            else:
                view_label = f"{view_type} "
            self._data2ui_frame_view_contextmenu_items.append(
                {
                    "name": f"{view_label}Frame",
                    "glyph": "frame.svg",  # TODO: Better icon selection
                    "enabled_fn": lambda objects: self._menu_prim_is_frame(objects=objects),
                    "show_fn": [
                        lambda objects: self._menu_prim_is_ui_prim(objects=objects),
                    ],
                    "onclick_fn": lambda objects, view_type=view_type: self._execute_view_for_contextmenu(
                        objects=objects,
                        view_type=view_type,
                    ),
                }
            )

        # self._frame_view_data2ui_contextmenu = omni.kit.context_menu.add_menu(self._data2ui_frame_view_contextmenu_items, "MENU")

    def _unregister_frame_view_menus(self):
        if self._data2ui_frame_view_menu:
            from omni.kit.property.usd import PrimPathWidget

            for button in self._data2ui_frame_view_menu:
                PrimPathWidget.remove_button_menu_entry(button)
        self._data2ui_frame_view_menu = None
        self._data2ui_frame_view_contextmenu_items = None

    def _register_stage_context_menus(self):
        from omni.kit.context_menu import add_menu

        self._data2ui_stage_contextmenu_items = []
        if self._data2ui_frame_view_contextmenu_items:
            for item in self._data2ui_frame_view_contextmenu_items:
                self._data2ui_stage_contextmenu_items.append(item)
        if self._reorder_data2ui_contextmenu_items:
            for item in self._reorder_data2ui_contextmenu_items:
                self._data2ui_stage_contextmenu_items.append(item)

        self._stage_contextmenus = [
            add_menu(item, "MENU", "omni.kit.widget.stage") for item in self._data2ui_stage_contextmenu_items
        ]

    def _unregister_stage_context_menus(self):
        self._stage_contextmenus.clear()

    def _register_stage_icons(self):
        from omni.kit.widget.stage.stage_icons import StageIcons

        stage_icons = StageIcons()
        for prim_type in valid_ui_prim_types:
            stage_icons.set(f"{PRIM_NS}{prim_type}", ICON_PATH / f"{prim_type.lower()}.svg")

    def _unregister_property_widget(self):
        import omni.kit.window.property as p

        w = p.get_window()
        if w:
            w.unregister_widget("prim", "data2ui")
            self._registered_widget = False

    def _register_event_unloaders(self):
        self._usd_context = omni.usd.get_context()

        def on_usd_context_event(event: carb.eventdispatcher.Event):
            from .prims import create_prim_properties

            if event.event_name in ("omni.usd::stage:closed", "omni.usd::stage:opened"):
                self._shutdown_views()
            # Ensuring that all valid USD properties are properly exposed
            # The motiviating reason here was exposing the `selected` property from `ui.Widget`, without this
            # users would need to create a new primitive and copy/paste existing data and relink all the relationships.
            # Kit 111's usdrt stage is an ovstage view without the Fabric query API (GetPrimsWithTypeName), and it is not
            # published yet when the stage opens: find the UI prims on the authored USD stage instead.
            if event.event_name == "omni.usd::stage:opened" and (stage := omni.usd.get_context().get_stage()):  # type: ignore
                names_by_type = {PRIM_NS + name: name for name in valid_ui_prim_types}
                for prim in stage.Traverse():
                    if name := names_by_type.get(str(prim.GetTypeName())):
                        create_prim_properties(name, prim)

        # self._event_unloader = self._usd_context.get_stage_event_stream().create_subscription_to_pop(
        #     on_usd_context_event, name="Data2UI Unload Views"
        # )
        self._event_unloaders = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="Data2UI Unload Views",
                event_name=_event_name,
                on_event=on_usd_context_event,
            )
            for _event_name in ("omni.usd::stage:closed", "omni.usd::stage:opened")
        ]

    def _register_disable_attribute(self):
        from omni.kit.context_menu import add_menu
        from omni.kit.property.usd.usd_attribute_model import UsdBase

        def can_show(object):
            model = object.get("model", None)
            if not model:
                return False

            stage = model.stage
            if not stage:
                return False

            return isinstance(model, UsdBase) and any(ATTR_NS in str(path) for path in model.get_attribute_paths())

        def can_execute(object):
            model = object.get("model", None)
            if not model:
                return False

            stage = model.stage
            if not stage:
                return False

            paths = model.get_attribute_paths()
            return len(paths) == 1

        def on_execute(object):
            model = object.get("model", None)
            if not model:
                return

            paths = model.get_attribute_paths()
            ctx = omni.usd.get_context()
            if stage := ctx.get_stage():  # type: ignore
                if prop := stage.GetPropertyAtPath(paths[-1]):
                    state = prop.GetMetadata("customData") or {}
                    state[DISABLED_PROPERTY] = not state.get(DISABLED_PROPERTY, False)
                    prop.SetMetadata("customData", state)
            if sel := ctx.get_selection():
                sel.clear_selected_prim_paths()
                sel.set_selected_prim_paths([str(path.GetParentPath()) for path in paths], True)

        menu = {
            "name": "NoCodeToggle",
            "show_fn": can_show,
            "enabled_fn": can_execute,
            "onclick_fn": on_execute,
        }
        self._disable_menu_entry = add_menu(menu, "attribute", "omni.kit.property.usd")
