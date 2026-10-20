"""Provides utilities for capturing and building deep link state from USD scenes."""

__all__ = ["LinkBuilder"]

import carb
import omni.kit.app
import omni.usd
from omni.usd import UsdContext
from pxr import Sdf, Usd

from .ui.notification import post_notification


class LinkBuilder:
    """Captures current scene state for encoding.

    Args:
        usd_context (UsdContext): The USD context for scene operations.
        stage (Usd.Stage): The USD stage containing the scene data.
    """

    def __init__(self, usd_context: UsdContext, stage: Usd.Stage):
        """Initializes the LinkBuilder with USD context and stage for capturing scene state."""
        self._stage = stage
        self._usd_context = usd_context
        self._camera_properties_to_capture = tuple(
            carb.settings.get_settings().get("/exts/omni.web.deeplink/camera_properties_to_capture")
        )

    def destroy(self):
        """Cleans up references to the stage and USD context."""
        self._stage = None
        self._usd_context = None

    @staticmethod
    def _format_float(value: float, precision: int = 4) -> str:
        """Formats a float value to a string with specified precision, removing trailing zeros.

        Args:
            value (float): The float value to format.
            precision (int): Number of decimal places to include.

        Returns:
            str: Formatted float string with trailing zeros removed.
        """
        value_str = f"{value:.{precision}f}"
        while value_str.endswith("0"):
            value_str = value_str[:-1]
        if value_str.endswith("."):
            return value_str[:-1]
        return value_str

    def get_scene_info(self) -> dict:
        """Get current scene file path and type

        Returns:
            dict: {"stage": str} containing the stage URL
        """
        return {"stage": self._usd_context.get_stage_url()}

    # from omni.kit.viewport.menubar.camera
    def __ensure_valid_camera(self, stage, viewport_api, camera_path: Sdf.Path):
        def validate_camera(camera_path):
            if camera_path:
                prim = stage.GetPrimAtPath(camera_path)
                if prim:
                    return Sdf.Path(camera_path)
            return None

        # Check if the camera_path is actually a valid camera_path
        camera_path = validate_camera(camera_path)
        if camera_path:
            return camera_path

        # Check if the info is held in the stage metadata.
        try:
            # Wrap in a try-catch so failure reading metadata does not cascade to caller.
            camera_path = validate_camera(stage.GetMetadataByDictKey("customLayerData", "cameraSettings:boundCamera"))
            if camera_path:
                return camera_path
        except Tf.ErrorException as e:
            carb.log_error(f"Error reading Usd.Stage's boundCamera metadata {e}")

        # Fallback to implicit Perspective if possible (it is deterministic)
        camera_path = validate_camera("/OmniverseKit_Persp")
        if camera_path:
            return camera_path

        return None

    def get_camera_state(self) -> dict:
        """Capture active camera state

        Returns:
            dict: Camera parameters (position, rotation, FOV, etc.)
        """
        import omni.kit.viewport.utility

        viewport_api = omni.kit.viewport.utility.get_active_viewport()
        current_camera_path = self.__ensure_valid_camera(self._stage, viewport_api, viewport_api.camera_path)
        if not current_camera_path:
            post_notification(f"Failed to find valid camera", info=False, duration=30)
            return {}

        camera_dict = {"camera": current_camera_path.pathString}
        camera_prim = self._stage.GetPrimAtPath(current_camera_path)
        # save all properties of the camera prim
        for property in camera_prim.GetProperties():
            self._add_property_to_dict(property, camera_dict)

        for prim in camera_prim.GetChildren():
            if not omni.usd.is_hidden_type(prim):
                for property in prim.GetProperties():
                    carb.log_warn(f"skipping child property: {prim.GetPath()}.{property.GetName()}")

        return {"camera": camera_dict}

    def get_time_state(self) -> dict:
        """Capture current time sample and FPS

        Returns:
            dict: {"time": dict} containing current time information
        """
        time_dict = {}
        try:
            import omni.timeline

            timeline = omni.timeline.get_timeline_interface()
            time_dict["current_time"] = LinkBuilder._format_float(timeline.get_current_time())
        except ModuleNotFoundError:
            pass

        return {"time": time_dict}

    def _add_unknown_type_to_dict(self, value: any, name: str, dict: dict):
        """Adds properties with unknown types to the dictionary as formatted strings.

        Args:
            value (any): The property value to convert and add.
            name (str): The property name to use as the dictionary key.
            dict (dict): The target dictionary to add the property to.
        """
        type_name = type(value).__name__
        if all(isinstance(x, float) for x in value):
            value_str = ",".join([LinkBuilder._format_float(x) for x in value])
        elif all(isinstance(x, str) for x in value):
            value_str = ",".join([f"{x}" for x in value])
        else:
            value_str = str(value)
            if value_str.startswith("[") and value_str.endswith("]"):
                value_str = value_str[1:-1]
            if value_str.startswith("(") and value_str.endswith(")"):
                value_str = value_str[1:-1]

        dict[name] = f"{type_name}({value_str})"

    def _add_property_to_dict(self, property: Usd.Property, dict: dict):
        """Adds a USD property to the dictionary with appropriate type formatting.

        Args:
            property (Usd.Property): The USD property to add to the dictionary.
            dict (dict): The target dictionary to add the property to.
        """
        if type(property) == Usd.Relationship:
            return

        name = property.GetName()
        # filter which properties to capture
        if self._camera_properties_to_capture and not name.startswith(self._camera_properties_to_capture):
            return

        if name and name not in dict:
            value = property.Get()
            if not value:
                carb.log_warn(f"Property {name} has no value")
                return

            type_name = type(value).__name__
            match type_name:
                case "str":
                    dict[name] = f'"{value}"'
                case "int":
                    dict[name] = f"{type_name}({str(value)})"
                case "float":
                    dict[name] = f"{type_name}({LinkBuilder._format_float(value)})"
                case "bool":
                    dict[name] = str(value)
                case _:
                    self._add_unknown_type_to_dict(value, name, dict)
