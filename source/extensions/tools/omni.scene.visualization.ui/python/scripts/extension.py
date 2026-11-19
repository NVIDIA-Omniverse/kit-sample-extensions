import omni.ext
import omni.kit.app
import omni.kit.property.geometry
from pxr import UsdGeom

from . import common
from .sceneviz_actions import deregister_actions, register_actions


class PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._visualization_preferences = None

        self._hooks = []

        manager = omni.kit.app.get_app().get_extension_manager()
        self._hooks.append(
            manager.subscribe_to_extension_enable(
                on_enable_fn=lambda _: self._register_preferences(),
                on_disable_fn=lambda _: self._unregister_preferences(),
                ext_name="omni.kit.window.preferences",
                hook_name="omni.scene.visualization.ui omni.kit.window.preferences listener",
            )
        )

        self._ext_id_no_version = ext_id.split("-")[0]
        register_actions(self._ext_id_no_version)
        self._register_custom_attributes()

    def on_shutdown(self):
        self._deregister_custom_attributes()
        deregister_actions(self._ext_id_no_version)
        self._hooks = None
        self._unregister_preferences()

    def _register_preferences(self):
        from omni.kit.window.preferences import register_page

        from .visualization_page import VisualizationPreferences

        self._visualization_preferences = register_page(VisualizationPreferences())

    def _unregister_preferences(self):
        if self._visualization_preferences:
            from omni.kit.window.preferences import unregister_page

            unregister_page(self._visualization_preferences)
            self._visualization_preferences = None

    def _register_custom_attributes(self):

        # Predicates for showing or hiding placeholder custom attributes
        def is_a_mesh(prim):
            return prim.IsA(UsdGeom.Mesh)

        def is_a_curve(prim):
            return prim.IsA(UsdGeom.BasisCurves)

        def is_a_mesh_or_curve(prim):
            return is_a_mesh(prim) or is_a_curve(prim)

        inst = omni.kit.property.geometry.get_instance()
        if inst:
            inst.register_custom_visual_attribute(
                common.DRAW_POINTS_ATTR, common.TOGGLE_POINTS, "bool", False, is_a_mesh_or_curve
            )
            inst.register_custom_visual_attribute(
                common.DRAW_NORMALS_ATTR, common.TOGGLE_NORMALS, "bool", False, is_a_mesh_or_curve
            )
            inst.register_custom_visual_attribute(
                common.DRAW_WIREFRAME_ATTR, common.TOGGLE_WIREFRAME, "bool", False, is_a_mesh_or_curve
            )
            inst.register_custom_visual_attribute(
                common.DRAW_TANGENTS_ATTR, common.TOGGLE_TANGENTS, "bool", False, is_a_curve
            )
            inst.register_custom_visual_attribute(
                common.USE_VERTEX_COLOR_ATTR, common.TOGGLE_VERTEX_COLOR, "bool", False, is_a_mesh_or_curve
            )

    def _deregister_custom_attributes(self):
        inst = omni.kit.property.geometry.get_instance()
        if inst:
            inst.deregister_custom_visual_attribute(common.DRAW_POINTS_ATTR)
            inst.deregister_custom_visual_attribute(common.DRAW_NORMALS_ATTR)
            inst.deregister_custom_visual_attribute(common.DRAW_WIREFRAME_ATTR)
            inst.deregister_custom_visual_attribute(common.DRAW_TANGENTS_ATTR)
            inst.deregister_custom_visual_attribute(common.USE_VERTEX_COLOR_ATTR)
