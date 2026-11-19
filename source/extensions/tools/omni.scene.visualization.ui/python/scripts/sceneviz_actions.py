import omni.kit.actions.core
import omni.scene.visualization.core

from . import common


def register_actions(extension_id):
    def on_action(menu_item):
        visualization_interface = omni.scene.visualization.core.acquire_interface()
        if menu_item == common.TOGGLE_POINTS:
            visualization_interface.toggle_points()
        elif menu_item == common.TOGGLE_NORMALS:
            visualization_interface.toggle_normals()
        elif menu_item == common.TOGGLE_WIREFRAME:
            visualization_interface.toggle_wireframe()
        elif menu_item == common.TOGGLE_TANGENTS:
            visualization_interface.toggle_tangents()
        elif menu_item == common.TOGGLE_VERTEX_COLOR:
            visualization_interface.toggle_vertex_color()

    action_registry = omni.kit.actions.core.get_action_registry()
    actions_tag = "Scene Visualization Actions"

    action_registry.register_action(
        extension_id,
        "scene_visualization_toggle_points",
        lambda: on_action(common.TOGGLE_POINTS),
        display_name=common.TOGGLE_POINTS,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "scene_visualization_toggle_normals",
        lambda: on_action(common.TOGGLE_NORMALS),
        display_name=common.TOGGLE_NORMALS,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "scene_visualization_toggle_wireframe",
        lambda: on_action(common.TOGGLE_WIREFRAME),
        display_name=common.TOGGLE_WIREFRAME,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "scene_visualization_toggle_tangents",
        lambda: on_action(common.TOGGLE_TANGENTS),
        display_name=common.TOGGLE_TANGENTS,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "scene_visualization_toggle_vertex_color",
        lambda: on_action(common.TOGGLE_VERTEX_COLOR),
        display_name=common.TOGGLE_VERTEX_COLOR,
        tag=actions_tag,
    )


def deregister_actions(extension_id):
    action_registry = omni.kit.actions.core.get_action_registry()
    action_registry.deregister_all_actions_for_extension(extension_id)
