import carb
import carb.settings
import omni.kit.commands
import omni.kit.context_menu
import omni.ui
from pxr import Sdf, Usd, UsdGeom


class ViewportWatcher:
    def __init__(self):
        self._camera_menu = None
        self._camera_prim = None

    def _get_selected_prim_paths(self):
        context = omni.usd.get_context()
        selection: omni.usd.Selection = context.get_selection()
        return selection.get_selected_prim_paths()

    def on_startup(self):
        context_menu: omni.kit.context_menu.ContextMenuExtension = omni.kit.context_menu.get_instance()
        if context_menu is None:
            return

        self.setup_menu_items()

    def on_shutdown(self):
        self.clean_menu_items()
        self._camera_menu = None

    def create_menu_entry_from_settings(name, setting_path):
        settings = carb.settings.get_settings()
        menu = {
            "name": name,
            "onclick_fn": lambda object: self._on_filter_changed(setting_path, not settings.get(setting_path)),
            "checked_fn": lambda object: settings.get(setting_path),
        }

        return omni.kit.context_menu.add_menu(menu, "options", "omni.anim.camera_tool")

    def _get_camera_prim(self):
        """Returns the current camera's frustum"""
        # Get the camera prim
        viewport_api = self.get_active_viewport()
        # carb.log_warn(f"viewport_api {viewport_api}")
        stage = viewport_api.stage
        if stage:
            self._camera_path = viewport_api.camera_path
            self._camera_prim = stage.GetPrimAtPath(self._camera_path)
            if self._camera_prim is not None:
                return self._camera_prim

        return None

    def _get_current_world_transform(self, stage, prim):
        timeline = omni.timeline.get_timeline_interface()
        timecode = timeline.get_current_time() * stage.GetTimeCodesPerSecond()
        prim_world_mtx = omni.usd.get_world_transform_matrix(prim, timecode)
        return prim_world_mtx

    def _update_camera_focus_distance(self, camera_prim, new_distance, time):
        camera = UsdGeom.Camera(camera_prim)
        focus_distance_attr = camera.GetFocusDistanceAttr()
        # TODO: should have a proper default value
        pre_focus_distance = 0.0
        if focus_distance_attr:
            pre_focus_distance = focus_distance_attr.Get()

        omni.kit.commands.execute(
            "ChangePropertyCommand",
            prop_path=str(focus_distance_attr.GetPath()),
            value=new_distance,
            prev=pre_focus_distance,
            timecode=Usd.TimeCode.Default(),
            type_to_create_if_not_exist=Sdf.ValueTypeNames.Float,
        )
        # carb.log_warn(f"_update_camera_focus_distance Path={focus_distance_attr.GetPath()} | pre_focus_distance={pre_focus_distance} new_distance={new_distance}")

    def _focus_on_target_list(self, target_list):
        import numpy as np

        # ----------------------------------------------------------------------------
        # Setup
        stage = omni.usd.get_context().get_stage()
        timeline = omni.timeline.get_timeline_interface()
        timecode = timeline.get_current_time() * stage.GetTimeCodesPerSecond()

        # carb.log_warn(f"Current Stage {stage} timecode={timecode}")

        # ----------------------------------------------------------------------------
        # Get the current camera
        current_camera = self._get_camera_prim()
        if current_camera is None:
            return False

        cam_xform = self._get_current_world_transform(stage, current_camera)
        campos = cam_xform[3]
        # carb.log_warn(f"Current Camera {current_camera} campos={campos}")

        # ----------------------------------------------------------------------------
        # Build a focus target range that collects all targets in the list
        range_min = 100000
        range_max = -100000
        for pos in target_list:
            range = np.linalg.norm(np.array(pos - np.array([campos[0], campos[1], campos[2]])))
            if range < range_min:
                range_min = range
            if range > range_max:
                range_max = range
        # carb.log_warn(f"Range_min={range_min} range_max={range_max}")

        # ----------------------------------------------------------------------------
        # Set the Focal Distance to encompass all targets
        self._update_camera_focus_distance(current_camera, range_min, timeline.get_current_time())
        return True

    def focus_on_pos_list(self, target_list):
        self._focus_on_target_list(target_list)
        # carb.log_warn(f"Target list {target_list}")
        return

    def focus_on_viewport(self, objects):
        # ----------------------------------------------------------------------------
        # Focus on a physics hit in the viewport
        # ----------------------------------------------------------------------------
        # carb.log_warn(f"Target objects {objects}")

        return

    def focus_on_target(self):
        # ----------------------------------------------------------------------------
        # Focus on a list of targets currently selected
        # ----------------------------------------------------------------------------

        # ----------------------------------------------------------------------------
        # Get the current list of targets
        target_selections = self._get_selected_prim_paths()
        # carb.log_warn(f"Target selections {target_selections}")
        target_list = []
        viewport_api = self.get_active_viewport()
        stage = viewport_api.stage
        if stage:
            for selection in target_selections:
                prim = stage.GetPrimAtPath(selection)
                # carb.log_warn(f"Selection {selection} prim {prim}")
                xform = self._get_current_world_transform(stage, prim)
                target_list += [xform]
            # carb.log_warn(f"Xform {xform} Target list {target_list}")
        return True

    @staticmethod
    def get_active_viewport():
        from omni.kit.viewport.utility import get_active_viewport

        return get_active_viewport()

    def setup_menu_items(self):
        def is_camera(objects):
            target_selections = self._get_selected_prim_paths()
            if target_selections is None or len(target_selections) < 1:
                return False

            if self.get_active_viewport() is not None:
                return True

            return False

        def is_hit_object(objects):
            if self.get_active_viewport() is not None:
                return True

            return False

        def focus_on_target(objects):
            # carb.log_warn(f"Target objects {objects}")
            self.focus_on_target()
            return True

        def focus_on_mouse_pos(objects):
            # ----------------------------------------------------------------------------
            # Focus on the world position mouse position
            # ----------------------------------------------------------------------------
            # carb.log_warn(f"Mouse Position objects {objects} mouse_pos={objects['mouse_pos']}")
            target_list = [objects["mouse_pos"]]
            self.focus_on_pos_list(target_list)

        focus_on_target_menu = {
            "name": "Focus on Target",
            "glyph": "menu_search.svg",
            "show_fn": [is_camera],
            "onclick_fn": focus_on_target,
        }
        focus_here_menu = {
            "name": "Focus Here",
            "glyph": "menu_search.svg",
            "show_fn": [is_hit_object],
            "onclick_fn": focus_on_mouse_pos,
        }

        # self._target_menu = omni.kit.context_menu.add_menu(focus_on_target_menu, "MENU", "omni.kit.window.viewport")
        self._here_menu = omni.kit.context_menu.add_menu(focus_here_menu, "MENU", "omni.kit.window.viewport")
        return

    def clean_menu_items(self):
        self._target_menu = None
        self._here_menu = None
