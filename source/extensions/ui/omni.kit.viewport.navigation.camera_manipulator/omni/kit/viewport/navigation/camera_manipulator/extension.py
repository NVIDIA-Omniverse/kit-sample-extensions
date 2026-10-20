import functools
from contextlib import suppress

import carb.eventdispatcher
import carb.settings
import carb.tokens
import omni.ext
import omni.kit.app
import omni.usd
from omni.kit.viewport.navigation.core import IMAGE_SIZE, ViewportNavigationButton, get_navigation_bar
from omni.kit.viewport.registry import RegisterScene

from .button_manager import ButtonManager
from .common.constant import BUTTON_VISIBLILITY_PATH, NAVIGATION_TOOL_DEFAULT_OPERATION
from .navigation_engine import NavigationEngine
from .navigation_scene import NavigationScene
from .utils import fit_camera, set_camera_fov, unroll_camera

__all__ = ["Extension"]

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.camera_manipulator/"
CAMERA_FOV_PATH = "/persistent/exts/omni.kit.viewport.navigation.camera_manipulator/fov"
USE_FSD = "/app/useFabricSceneDelegate"


class Extension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        navigaiton_bar = get_navigation_bar()
        tokens = carb.tokens.get_tokens_interface()
        icon_path = tokens.resolve(f"${{{self._ext_name}}}/icons/")

        self._button_manager = ButtonManager()
        self._navigation_engine = NavigationEngine(self._button_manager)
        self._settings = carb.settings.get_settings()
        name_list = [
            x
            for x in NavigationEngine.get_name_list()
            if self._settings.get_as_bool(f"{BUTTON_VISIBLILITY_PATH}{x}_visible")
        ]
        default_operation = self._settings.get(NAVIGATION_TOOL_DEFAULT_OPERATION)
        with navigaiton_bar:
            for name in name_list:
                true_image = icon_path + f"nav{name.capitalize()}_active_dark.svg"
                false_image = icon_path + f"nav{name.capitalize()}_dark.svg"

                order_setting = SETTINGS_ROOT + name + "_order"
                visible_setting = SETTINGS_ROOT + name + "_visible"

                style = {
                    "Navigation.Button.Image::" + f"{name}": {"image_url": f"{false_image}"},
                    "Navigation.Button.Image::" + f"{name}:checked": {"image_url": f"{true_image}"},
                }
                button = ViewportNavigationButton(
                    name,
                    IMAGE_SIZE,
                    visible_setting_path=visible_setting,
                    order_setting_path=order_setting,
                    clicked_fn=functools.partial(self._button_manager.on_button_clicked, name),
                    build_tooltip_fn=getattr(self._button_manager, f"_build_{name}_tooltip"),
                    style=style,
                )
                if name == default_operation:
                    button.set_state(True)
                else:
                    button.set_state(False)
                self._button_manager.add_button(name, button)

        self._scene = RegisterScene(NavigationScene, "omni.kit.tool.navigation.scene")

        manager = omni.kit.app.get_app().get_extension_manager()
        self._hook = manager.subscribe_to_extension_enable(
            on_enable_fn=lambda _: self._register_preferences(),
            on_disable_fn=lambda _: self._unregister_preferences(),
            ext_name="omni.kit.window.preferences",
            hook_name="omni.kit.viewport.navigation.camera_manipulator omni.kit.window.preferences listener",
        )

        # FIXME: This extension only works on the default UsdContext
        usd_context = omni.usd.get_context()
        self._stage_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="omni.kit.viewport.navigation.camera_manipulator.NavigationCameraSetup",
            event_name=usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_open_event,
        )

        self._camera_fov_changed_sub = self._settings.subscribe_to_node_change_events(CAMERA_FOV_PATH, set_camera_fov)

    def _on_stage_open_event(self, *args, **kwargs) -> None:
        set_camera_fov()
        # Check if the perspective camera is within the scene bonds.
        # If outside, the camera will be adjusted to be within the
        # scene contents and look at its center, including unrolling.
        # OMFP-3068: Run ::fit_camera only if FSD is active.
        result = fit_camera() if self._settings.get(USE_FSD) else False
        if not result:
            # Otherwise just unroll, it if needed.
            unroll_camera()

    def on_shutdown(self):  # pragma: no cover
        self._unregister_preferences()
        self._hook = None
        self._navigation_engine.destroy()
        self._button_manager.destroy()
        self._scene = None
        self._stage_event_sub = None
        self._camera_fov_changed_sub = None

    def _register_preferences(self):
        try:
            from omni.kit.window.preferences import register_page

            from .preferences_page import CameraManipPreferences

            self._preferences = register_page(CameraManipPreferences())
        except ImportError:
            pass

    def _unregister_preferences(self):
        try:
            if self._preferences:
                from omni.kit.window.preferences import unregister_page

                unregister_page(self._preferences)
                self._preferences = None
        except ImportError:
            pass
