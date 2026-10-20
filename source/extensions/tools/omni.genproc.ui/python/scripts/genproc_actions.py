import omni.kit.actions.core

from . import menu_common


def register_actions(extension_id, curve_menu_cls, get_menu_fn):
    action_registry = omni.kit.actions.core.get_action_registry()
    actions_tag = "General Proceduralism Actions"

    action_registry.register_action(
        extension_id,
        "curve_from_xformables",
        lambda: get_menu_fn()._on_menu_click(menu_common.CURVE_FROM_XFORMABLES),
        display_name=menu_common.CURVE_FROM_XFORMABLES,
        description=menu_common.CURVE_FROM_XFORMABLES,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "get_curve_data",
        lambda: get_menu_fn()._on_menu_click(menu_common.GET_CURVE_DATA),
        display_name=menu_common.GET_CURVE_DATA,
        description=menu_common.GET_CURVE_DATA,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "tag_curves_with_ramp",
        lambda: get_menu_fn()._on_menu_click(menu_common.TAG_CURVES_WITH_RAMP),
        display_name=menu_common.TAG_CURVES_WITH_RAMP,
        description=menu_common.TAG_CURVES_WITH_RAMP,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "resample_curves",
        lambda: get_menu_fn()._on_menu_click(menu_common.RESAMPLE_CURVES),
        display_name=menu_common.RESAMPLE_CURVES,
        description=menu_common.RESAMPLE_CURVES,
        tag=actions_tag,
    )

    action_registry.register_action(
        extension_id,
        "create_curve_deformer",
        curve_menu_cls._on_create_curve_clicked,
        display_name="Create Curve Deformer",
        description="Create Curve Deformer",
        tag=actions_tag,
    )


def deregister_actions(extension_id):
    action_registry = omni.kit.actions.core.get_action_registry()
    action_registry.deregister_all_actions_for_extension(extension_id)
