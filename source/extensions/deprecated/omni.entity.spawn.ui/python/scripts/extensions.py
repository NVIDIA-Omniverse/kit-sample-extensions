import os.path

import omni.ext
import omni.kit.menu.utils
import omni.kit.ui
from omni.graph.ui import add_create_menu_type, remove_create_menu_type
from omni.kit.menu.utils import MenuItemDescription

# from .wizard_window import SpawnEntityWizardWindow
from .prop_widget import SpawnGraphPropWidget
from .utils import create_default_spawn_graph

EXTENSION_NAME = "Spawn Entity"
MENU_PATH = "Spawn Graph"

g_spawn_instance = None


class SpawnEntityExtension(omni.ext.IExt):
    def get_name(self):
        return EXTENSION_NAME

    def on_startup(self, ext_id):
        global g_spawn_instance
        g_spawn_instance = self

        global omni
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        icon_path = os.path.join(ext_path, "data/icons")
        # self._wizard_window = SpawnEntityWizardWindow(name="Entity Spawn Graph Wizard", icon_path=icon_path)
        # self._wizard_window.on_startup()
        # SpawnGraphPropWidget.startup()

        # self._menu = [
        #     MenuItemDescription(
        #         header="Examples"),
        #     MenuItemDescription(
        #         name="Entity Spawn System",
        #         glyph="menu_graph.svg",
        #         #onclick_fn=self._wizard_window._build_spawn_graph,
        #         onclick_fn=create_default_spawn_graph,
        #     )]
        # self._visual_scripting_menu = [MenuItemDescription(name="Visual Scripting", glyph="menu_graph.svg", sub_menu=self._menu, appear_after="Action Graph")]

        # omni.kit.menu.utils.add_menu_items(self._visual_scripting_menu, "Create", 0, True)

        # # Register custom UI for graph nodes
        # self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
        #     self._wizard_window.on_update, name="Spawn Entity Window Update"
        # )

        # if omni.kit.app.get_app().get_extension_manager().is_extension_enabled("omni.graph.ui"):
        #     import omni.graph.ui
        #     omni.graph.ui.ComputeNodeWidget.get_instance().add_template_path(__file__)

    def on_shutdown(self):
        global g_spawn_instance
        g_spawn_instance = None
        # SpawnGraphPropWidget.shutdown()
        # self._wizard_window.on_shutdown()
        # self._wizard_window = None
        # omni.kit.menu.utils.remove_menu_items(self._menu, "Create")
        # self._menu.clear()
        # self._update_sub = None


def get_instance() -> SpawnEntityExtension:
    return g_spawn_instance
