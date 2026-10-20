import AnimationSchema
import carb
import omni.kit.app
from omni.anim.curve.core import (
    gen_comp_attr_path,
    get_animation_prim_path,
    get_curve_plugin,
    get_curvekey_clipboard,
    get_keys,
    set_curvekey_clipboard,
)
from omni.kit.property.usd.usd_attribute_model import UsdBase as UsdBase
from pxr import Gf, Sdf, Usd

# In control_state_manager.py the timesample key and curve priority is 20 and 30
# Set it to a smaller value than 20 to take the priority
ANIM_KEY_CTL_STATE_PRIORITY = 18
ANIM_CURVE_CTL_STATE_PRIORITY = 19

# Move the `clipboard` to global variables to enable `clear` operation
LIST_SCHEMA_KEYS_FOR_COPY_ANIMATION = []
# You MUST be very careful when assigning values to this list!
# You'd better use xxx.append(), xxx.clear(), etc, instead of directly assigning values to it!


def clear_animation_data_clipboard():
    LIST_SCHEMA_KEYS_FOR_COPY_ANIMATION.clear()


class AnimContextMenu:
    def __init__(self):
        self._context_menu_key_menus()
        self._context_menu_curve_menus()
        self._status_icon_anim_key()

    def on_shutdown(self):
        self._set_key_entry = None
        self._remove_key_entry = None
        self._remove_anim_entry = None
        self._anim_key_separator_menu = None
        self._anim_separator_menu = None
        self._copy_animation_entry = None
        self._paste_animation_entry = None
        self._copy_key_entry = None
        self._paste_key_entry = None

        try:
            from omni.kit.property.usd.control_state_manager import ControlStateManager
        except ModuleNotFoundError:
            return

        cs_mgr = ControlStateManager.get_instance()
        if self._flag_anim_curve:
            cs_mgr.unregister_control_state(self._flag_anim_curve)
            self._flag_anim_curve = None
        if self._flag_anim_key:
            cs_mgr.unregister_control_state(self._flag_anim_key)
            self._flag_anim_key = None

    def _has_curve(prim, curve_name):
        curves = get_curve_plugin().get_curves(str(prim.GetPath()))
        if curves:
            return curve_name in curves
        else:
            return False

    def _has_key(prim, curve_name, time_code):
        time = int(
            time_code.GetValue() / prim.GetStage().GetTimeCodesPerSecond() * get_curve_plugin().get_ticks_per_second()
        )

        curves = get_curve_plugin().get_curves(str(prim.GetPath()))
        curve = curves.get(curve_name)
        if curve is None:
            return False

        for key in curve.keys:
            if key.time == time:
                return True

        return False

    @staticmethod
    def _has_anim_curve_key(usd_model):
        from omni.kit.property.usd.usd_attribute_model import (
            GfVecAttributeModel,
            GfVecAttributeSingleChannelModel,
            TfTokenAttributeModel,
            UsdAttributeModel,
        )

        attr_paths = usd_model.get_attribute_paths()
        has_curve = has_key = False
        if not usd_model._stage:
            return has_curve, has_key
        # GfVecAttributeSingleChannelModel can set single component of a vector separately as well as a bundle
        if isinstance(usd_model, GfVecAttributeSingleChannelModel):
            post_fix = ":x"
            if usd_model._channel_index == 0:
                post_fix = ":x"
            elif usd_model._channel_index == 1:
                post_fix = ":y"
            elif usd_model._channel_index == 2:
                post_fix = ":z"
            elif usd_model._channel_index == 3:
                post_fix = ":w"
            elif usd_model._channel_index == -1:
                post_fix = ":x"
            else:
                carb.log_error("Invalid UsdModel channel index!")
                return has_curve, has_key
            for attr_path in attr_paths:
                prim = usd_model._stage.GetPrimAtPath(attr_path.GetPrimPath())
                if prim:
                    attr = prim.GetAttribute(attr_path.name)
                    if __class__._has_curve(prim, attr_path.name + post_fix):
                        has_curve = True
                    if __class__._has_key(prim, attr_path.name + post_fix, usd_model.get_current_time_code()):
                        has_key = True
            return has_curve, has_key
        # A normal UsdAttributeModel or a GfVecAttributeModel can only set a key without component(channel) info
        elif isinstance(usd_model, UsdAttributeModel):
            for attr_path in attr_paths:
                prim = usd_model._stage.GetPrimAtPath(attr_path.GetPrimPath())
                if prim:
                    attr = prim.GetAttribute(attr_path.name)
                    if __class__._has_curve(prim, attr_path.name + ":x"):
                        has_curve = True
                    if __class__._has_key(prim, attr_path.name + ":x", usd_model.get_current_time_code()):
                        has_key = True
        elif isinstance(usd_model, GfVecAttributeModel):
            for attr_path in attr_paths:
                prim = usd_model._stage.GetPrimAtPath(attr_path.GetPrimPath())
                if prim:
                    attr = prim.GetAttribute(attr_path.name)
                    if __class__._has_curve(prim, attr_path.name + ":x"):
                        has_curve = True
                    if __class__._has_key(prim, attr_path.name + ":x", usd_model.get_current_time_code()):
                        has_key = True
                    if has_curve and has_key:
                        break
                    comp_num = usd_model._get_comp_num()
                    if comp_num > 1:
                        if __class__._has_curve(prim, attr_path.name + ":y"):
                            has_curve = True
                        if __class__._has_key(prim, attr_path.name + ":y", usd_model.get_current_time_code()):
                            has_key = True
                        if has_curve and has_key:
                            break
                    if comp_num > 2:
                        if __class__._has_curve(prim, attr_path.name + ":z"):
                            has_curve = True
                        if __class__._has_key(prim, attr_path.name + ":z", usd_model.get_current_time_code()):
                            has_key = True
                        if has_curve and has_key:
                            break
                    if comp_num > 3:
                        if __class__._has_curve(prim, attr_path.name + ":w"):
                            has_curve = True
                        if __class__._has_key(prim, attr_path.name + ":w", usd_model.get_current_time_code()):
                            has_key = True
                        if has_curve and has_key:
                            break
        elif isinstance(usd_model, TfTokenAttributeModel):
            for attr_path in attr_paths:
                prim = usd_model._stage.GetPrimAtPath(attr_path.GetPrimPath())
                if not prim:
                    continue

                curve_name = attr_path.name + ":x"

                if __class__._has_curve(prim, curve_name):
                    has_curve = True
                if __class__._has_key(prim, curve_name, usd_model.get_current_time_code()):
                    has_key = True
        else:
            pass
        return has_curve, has_key

    @staticmethod
    def can_show_anim_authoring_menu(object):
        model = object.get("model", None)
        return isinstance(model, UsdBase) if model else False

    def _context_menu_key_menus(self):
        try:
            import omni.kit.context_menu
        except ModuleNotFoundError:
            return

        menu_sep = {
            "name": "",
        }
        self._anim_key_separator_menu = omni.kit.context_menu.add_menu(menu_sep, "attribute", "omni.kit.property.usd")

        # when apply_last_rule is `True`, only the last selected object would be considered as target;
        # e.g. when you select A and B, C three objects then `Copy Key`, if apply_last_rule is `True`
        # only C's key will be copied.
        def _get_curve_key_info(object, apply_last_rule: bool):
            model = object.get("model", None)
            if not model:
                carb.log_warn("Illegal model in AnimContextMenu")
                return None, None, None
            attribute_paths = object.get("attribute_paths", [])
            if not attribute_paths:
                carb.log_warn("Unexpected code path in AnimContextMenu")
                return None, None, None
            time_code = _get_time_code(object)
            if not time_code:
                return None, None, None

            curve_paths = []
            if apply_last_rule:
                attribute_paths = [attribute_paths[-1]]
            for attribute_path in attribute_paths:
                component_index = object.get("comp_index", -1)
                # component_index is -1, means copy whole attribute
                if component_index == -1:
                    curve_paths.append(attribute_path.pathString)
                else:
                    curve_paths.append(
                        gen_comp_attr_path(attribute_path.pathString, component_index, "AnimContextMenu")
                    )

            return model._stage, time_code, curve_paths

        def _get_time_code(object):
            model = object.get("model", None)
            if not model:
                carb.log_warn("Illegal model in AnimContextMenu")
                return None, None, None
            component_index = object.get("comp_index", -1)
            if component_index == -1:
                import omni.timeline

                cur_time = (
                    omni.timeline.get_timeline_interface().get_tentative_time() * model._stage.GetTimeCodesPerSecond()
                )
                time_code = Usd.TimeCode(round(cur_time))
            else:
                time_code = object.get("time_code", Usd.TimeCode.Default())
            return time_code

        def can_enable_set_key(object):
            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", None)
            if attribute_paths is None:
                return False
            for attribute_path in attribute_paths:
                if not get_curve_plugin().is_attr_supported(str(attribute_path)):
                    return False
            return True

        def on_set_key(object):
            from omni.kit.property.usd.usd_attribute_model import (
                GfVecAttributeModel,
                GfVecAttributeSingleChannelModel,
                TfTokenAttributeModel,
                UsdAttributeModel,
            )

            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", [])
            stage, time_code, curve_paths = _get_curve_key_info(object, False)
            comp_index = object.get("comp_index", -1)
            if not model:
                return
            if not stage:
                stage = model._stage

            if len(attribute_paths):
                with omni.kit.undo.group():
                    for attr_path in attribute_paths:
                        # prepare for getting the default tangent type token, if possible, and for getting real component indices.
                        attr = stage.GetObjectAtPath(attr_path)
                        prim = attr.GetPrim()
                        prim_path_str = str(prim.GetPath())
                        if comp_index == -1:
                            dimension = 1
                            value_type = attr.GetTypeName().type.pythonClass
                            if hasattr(value_type, "__isGfVec"):
                                dimension = value_type.dimension
                            real_comp_indices = range(dimension)
                        else:
                            real_comp_indices = [comp_index]

                        for real_comp_index in real_comp_indices:
                            if real_comp_index == 0:
                                postfix = ":x"
                            elif real_comp_index == 1:
                                postfix = ":y"
                            elif real_comp_index == 2:
                                postfix = ":z"
                            elif real_comp_index == 3:
                                postfix = ":w"
                            data_attr_name = str(attr.GetName()) + postfix
                            runtime_curve = get_curve_plugin().get_curves(prim_path_str).get(data_attr_name)

                            if real_comp_index == 0:
                                command_postfix = "|x"
                            elif real_comp_index == 1:
                                command_postfix = "|y"
                            elif real_comp_index == 2:
                                command_postfix = "|z"
                            elif real_comp_index == 3:
                                command_postfix = "|w"
                            if runtime_curve == None:
                                # this is the first key of a new curve, preserveCurveShape is irrelevant. default_tangent_type_token is not known but is also not necessary to be known.
                                omni.kit.commands.execute("SetAnimCurveKeys", paths=[str(attr_path) + command_postfix])
                            else:
                                # get the default tangent type token
                                curve_api = AnimationSchema.AnimationCurveAPI(
                                    stage.GetPrimAtPath(runtime_curve.anim_data)
                                )
                                default_tangent_type_token = curve_api.GetDefaultTangentType(data_attr_name)

                                # Preserve shape, only if the default tangent type is auto. Else let the command to set the key with default tangent type considered internally.
                                omni.kit.commands.execute(
                                    "SetAnimCurveKeys",
                                    paths=[str(attr_path) + command_postfix],
                                    preserveCurveShape=default_tangent_type_token == "auto",
                                )

        menu = {
            "name": "Set Key",
            "show_fn": AnimContextMenu.can_show_anim_authoring_menu,
            "enabled_fn": can_enable_set_key,
            "onclick_fn": on_set_key,
        }
        self._set_key_entry = omni.kit.context_menu.add_menu(menu, "attribute", "omni.kit.property.usd")

        def on_remove_key(object):
            from omni.kit.property.usd.usd_attribute_model import (
                GfVecAttributeModel,
                GfVecAttributeSingleChannelModel,
                UsdAttributeModel,
            )

            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", [])
            stage, time_code, curve_paths = _get_curve_key_info(object, False)
            comp_index = object.get("comp_index", -1)

            if not model:
                return

            postfix = ""
            if comp_index == 0:
                postfix = "|x"
            elif comp_index == 1:
                postfix = "|y"
            elif comp_index == 2:
                postfix = "|z"
            elif comp_index == 3:
                postfix = "|w"
            command_attr_path = [str(attr_path) + postfix for attr_path in attribute_paths]

            omni.kit.commands.execute(
                "RemoveAnimCurveKeys", stage=model._stage, paths=command_attr_path, time=time_code
            )

        def can_enable_remove_key(object):
            has_curve, has_key = self._has_anim_curve_key(object.get("model", None))
            return has_key

        menu = {
            "name": "Remove Key",
            "show_fn": AnimContextMenu.can_show_anim_authoring_menu,
            "enabled_fn": can_enable_remove_key,
            "onclick_fn": on_remove_key,
        }
        self._remove_key_entry = omni.kit.context_menu.add_menu(menu, "attribute", "omni.kit.property.usd")

        def can_enable_copy_key(object):
            model = object.get("model", None)
            if model == None:
                return False
            else:
                _, has_key = self._has_anim_curve_key(model)
                return has_key

        def on_copy_key(object):
            stage, time_code, curve_paths = _get_curve_key_info(object, True)
            if stage:
                set_curvekey_clipboard(stage, curve_paths, Usd.TimeCode(time_code))

        menu = {
            "name": "Copy Key",
            "show_fn": AnimContextMenu.can_show_anim_authoring_menu,
            "enabled_fn": can_enable_copy_key,
            "onclick_fn": on_copy_key,
        }
        self._copy_key_entry = omni.kit.context_menu.add_menu(menu, "attribute", "omni.kit.property.usd")

        def enable_paste_key(object):

            # First of all, this attribute is able to be animated
            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", None)
            if attribute_paths is None:
                return False
            for attribute_path in attribute_paths:
                if not get_curve_plugin().is_attr_supported(str(attribute_path)):
                    return False
            return get_curvekey_clipboard().get_prim_count() > 0

        def on_paste_key(object):
            stage, time_code, curve_paths = _get_curve_key_info(object, False)
            if stage:
                # round the offset to integer frames
                omni.kit.commands.execute("PasteAnimCurveKeys", stage=stage, paths=curve_paths, time=time_code)

        menu = {
            "name": "Paste Key",
            "show_fn": AnimContextMenu.can_show_anim_authoring_menu,
            "enabled_fn": enable_paste_key,
            "onclick_fn": on_paste_key,
        }
        self._paste_key_entry = omni.kit.context_menu.add_menu(menu, "attribute", "omni.kit.property.usd")

    def _context_menu_curve_menus(self):
        try:
            import omni.kit.context_menu
        except ModuleNotFoundError:
            return

        menu_sep = {
            "name": "",
        }
        self._anim_separator_menu = omni.kit.context_menu.add_menu(menu_sep, "attribute", "omni.kit.property.usd")

        def can_enable_copy_animation(object):
            model = object.get("model", None)
            if model == None:
                return False
            else:
                has_curve, _ = self._has_anim_curve_key(model)
                return has_curve

        def on_copy_animation(object):
            # temptest. component_index when vector type?
            def get_num_components(object):
                from omni.kit.property.usd.usd_attribute_model import (
                    GfVecAttributeModel,
                    GfVecAttributeSingleChannelModel,
                    TfTokenAttributeModel,
                    UsdAttributeModel,
                )

                model = object.get("model", None)
                if isinstance(model, GfVecAttributeSingleChannelModel):
                    return 1
                elif (
                    isinstance(model, GfVecAttributeModel)
                    or isinstance(model, UsdAttributeModel)
                    or isinstance(model, TfTokenAttributeModel)
                ):
                    value = model.get_value()
                    # code borrowed from commands.py
                    value_vec_type = [
                        Gf.Vec2d,
                        Gf.Vec3d,
                        Gf.Vec4d,
                        Gf.Vec2f,
                        Gf.Vec3f,
                        Gf.Vec4f,
                        Gf.Vec2h,
                        Gf.Vec3h,
                        Gf.Vec4h,
                        Gf.Vec2i,
                        Gf.Vec3i,
                        Gf.Vec4i,
                    ]
                    value_len = value_type = None
                    if type(value) in value_vec_type:
                        value_len = len(value)
                        # We don't support vector type more than 4 components
                        if value_len > 4:
                            value_len = 4
                    elif type(value) == float or type(value) == int or type(value) == bool or type(value) == str:
                        value_len = 1

                    return value_len

            def get_curve_name(attr_name, component_index):
                if component_index == 0:
                    postfix = ":x"
                elif component_index == 1:
                    postfix = ":y"
                elif component_index == 2:
                    postfix = ":z"
                elif component_index == 3:
                    postfix = ":w"
                else:
                    carb.log_error("Unexpected code path in AnimContextMenu._get_curve_name()")
                    postfix = ""

                return attr_name + postfix

            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", [])
            time_code = object.get("time_code", Usd.TimeCode.Default())
            component_index = object.get("comp_index", -1)
            if not model:
                return

            attribute_path = attribute_paths[0] if len(attribute_paths) == 1 else None
            if attribute_path == None:
                carb.log_warn("Unexpected code path in AnimContextMenu.on_copy_animation()")
                return
            else:
                # init self._list_schema_keys_for_copy_animation as list of empty.
                clear_animation_data_clipboard()
                self._list_schema_keys_for_copy_animation += [[], [], [], []]

                # fill self._list_schema_keys_for_copy_animation
                user_prim = model._stage.GetPrimAtPath(attribute_path.GetPrimPath())
                data_prim_path = get_animation_prim_path(user_prim)
                if data_prim_path != None:
                    data_prim = model._stage.GetPrimAtPath(data_prim_path)
                    # fill component_indices
                    if component_index == -1:
                        num_components = get_num_components(object)
                        if num_components is None:
                            carb.log_warn("AnimContextMenu.on_copy_animation warning: no animation data is copied!")
                            return
                        component_indices = range(num_components)
                    else:
                        # duplicate so you can do 1=>n copy
                        component_indices = [component_index, component_index, component_index, component_index]

                    # fill _list_schema_keys_for_copy_animation
                    for key_list_index, component_index in enumerate(component_indices):
                        curve_name = get_curve_name(attribute_path.name, component_index)
                        schema_anim_data = AnimationSchema.AnimationData(data_prim)
                        self._list_schema_keys_for_copy_animation[key_list_index] = get_keys(user_prim, curve_name)
                else:
                    # the attribute has no curve animation data
                    # keep self._list_schema_keys_for_copy_animation as init.
                    pass

        def can_enable_paste_animation(object):

            # First of this attribute is able to be animated
            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", None)
            if attribute_paths is None:
                return False
            for attribute_path in attribute_paths:
                if not get_curve_plugin().is_attr_supported(str(attribute_path)):
                    return False
            # Second, we have something in our clipboard
            if id(self._list_schema_keys_for_copy_animation) != id(LIST_SCHEMA_KEYS_FOR_COPY_ANIMATION):
                carb.log_warn("AnimContextMenu's _list_schema_keys_for_copy_animation is overriden.")
            return False if len(self._list_schema_keys_for_copy_animation) == 0 else True

        def on_paste_animation(object):
            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", [])
            time_code = object.get("time_code", Usd.TimeCode.Default())
            component_index = object.get("comp_index", -1)
            if not model:
                return

            # tobe refactored ?
            postfix = ""
            if component_index == 0:
                postfix = "|x"
            elif component_index == 1:
                postfix = "|y"
            elif component_index == 2:
                postfix = "|z"
            elif component_index == 3:
                postfix = "|w"
            command_attr_path = [str(attr_path) + postfix for attr_path in attribute_paths]

            # command_attr_path0 = str(command_attr_path[0]) if len(command_attr_path) == 1 else None
            if command_attr_path == None:
                carb.log_warn("Unexpected code path in AnimContextMenu.on_paste_animation()")
                return
            else:
                omni.kit.commands.execute(
                    "PasteAnimCurves",
                    listSchemaKeys=self._list_schema_keys_for_copy_animation,
                    dstCurvePath=command_attr_path,
                )

        self._list_schema_keys_for_copy_animation = LIST_SCHEMA_KEYS_FOR_COPY_ANIMATION
        menu = {
            "name": "Copy Animation",
            "show_fn": AnimContextMenu.can_show_anim_authoring_menu,
            "enabled_fn": can_enable_copy_animation,
            "onclick_fn": on_copy_animation,
        }
        self._copy_animation_entry = omni.kit.context_menu.add_menu(menu, "attribute", "omni.kit.property.usd")

        menu = {
            "name": "Paste Animation",
            "show_fn": AnimContextMenu.can_show_anim_authoring_menu,
            "enabled_fn": can_enable_paste_animation,
            "onclick_fn": on_paste_animation,
        }
        self._paste_animation_entry = omni.kit.context_menu.add_menu(menu, "attribute", "omni.kit.property.usd")

        def on_remove_curve(object):
            from omni.kit.property.usd.usd_attribute_model import (
                GfVecAttributeModel,
                GfVecAttributeSingleChannelModel,
                UsdAttributeModel,
            )

            model = object.get("model", None)
            attribute_paths = object.get("attribute_paths", [])
            comp_index = object.get("comp_index", -1)
            if not model:
                return

            postfix = ""
            if comp_index == 0:
                postfix = "|x"
            elif comp_index == 1:
                postfix = "|y"
            elif comp_index == 2:
                postfix = "|z"
            elif comp_index == 3:
                postfix = "|w"
            command_attr_path = [str(attr_path) + postfix for attr_path in attribute_paths]

            omni.kit.commands.execute("RemoveAnimCurves", paths=command_attr_path)

            # This is a trick. We can't access GfVecAttributeChannelModel from GfVecAttributeModel
            # So we modified the USD data a little bit to trigger the control state update for all channels.
            if comp_index == -1 and isinstance(model, GfVecAttributeModel):
                for attribute_path in attribute_paths:
                    attr = model._stage.GetAttributeAtPath(attribute_path)
                    if attr:
                        import copy

                        attr_value = attr.Get()
                        attr_tmp = copy.copy(attr_value)
                        attr_tmp[0] = attr_tmp[0] + 0.0001
                        attr.Set(attr_tmp)
                        attr.Set(attr_value)
            else:
                model.update_control_state()

        def can_enable_remove_curve(object):
            has_curve, has_key = self._has_anim_curve_key(object.get("model", None))
            return has_curve

        menu = {
            "name": "Remove Animation",
            "show_fn": AnimContextMenu.can_show_anim_authoring_menu,
            "enabled_fn": can_enable_remove_curve,
            "onclick_fn": on_remove_curve,
        }
        self._remove_anim_entry = omni.kit.context_menu.add_menu(menu, "attribute", "omni.kit.property.usd")

    def _status_icon_anim_key(self):
        try:
            from omni.kit.property.usd.control_state_manager import ControlStateManager
            from omni.kit.property.usd.usd_attribute_model import (
                GfVecAttributeModel,
                GfVecAttributeSingleChannelModel,
                TfTokenAttributeModel,
                UsdAttributeModel,
            )
        except ModuleNotFoundError:
            return

        cs_mgr = ControlStateManager.get_instance()

        def on_refresh_anim_key(usd_model):
            has_curve, has_key = self._has_anim_curve_key(usd_model)
            return has_key, True

        def on_build_anim_key(has_state_flag, **kwargs):
            if not has_state_flag:
                return False, None, None
            usd_model = kwargs.get("model")

            def on_click_fn(*arg):
                attr_paths = usd_model.get_attribute_paths()
                comp_index = -1
                if isinstance(usd_model, GfVecAttributeSingleChannelModel):
                    comp_index = usd_model._channel_index
                postfix = ""
                if comp_index == 0:
                    postfix = "|x"
                elif comp_index == 1:
                    postfix = "|y"
                elif comp_index == 2:
                    postfix = "|z"
                elif comp_index == 3:
                    postfix = "|w"
                command_attr_path = [str(attr_path) + postfix for attr_path in attr_paths]
                omni.kit.commands.execute(
                    "RemoveAnimCurveKeys",
                    stage=usd_model._stage,
                    paths=command_attr_path,
                    time=usd_model.get_current_time_code(),
                )

            return True, on_click_fn, "Click to Remove a Key"

        path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)

        icon_anim_key = f"{path}/icons/AnimKey.svg"

        self._flag_anim_key = cs_mgr.register_control_state(
            on_refresh_anim_key, on_build_anim_key, icon_anim_key, ANIM_KEY_CTL_STATE_PRIORITY
        )

        def on_refresh_anim_curve(usd_model):
            has_curve, has_key = self._has_anim_curve_key(usd_model)
            return has_curve, True

        icon_anim_curve = f"{path}/icons//AnimCurve.svg"

        # Callback when the model only has curve but not key here: click it to add a key
        def on_build_anim_curve(has_state_flag, **kwargs):
            if not has_state_flag:
                return False, None, None
            usd_model = kwargs.get("model")

            def on_click_fn(*arg):
                attr_paths = usd_model.get_attribute_paths()
                comp_index = -1
                if isinstance(usd_model, GfVecAttributeSingleChannelModel):
                    comp_index = usd_model._channel_index
                postfix = ""
                if comp_index == 0:
                    postfix = "|x"
                elif comp_index == 1:
                    postfix = "|y"
                elif comp_index == 2:
                    postfix = "|z"
                elif comp_index == 3:
                    postfix = "|w"
                command_attr_path = [str(attr_path) + postfix for attr_path in attr_paths]

                if isinstance(usd_model, GfVecAttributeSingleChannelModel):
                    omni.kit.commands.execute(
                        "SetAnimCurveKeys", paths=command_attr_path, value=usd_model.get_value_as_float()
                    )
                elif (
                    isinstance(usd_model, GfVecAttributeModel)
                    or isinstance(usd_model, UsdAttributeModel)
                    or isinstance(usd_model, TfTokenAttributeModel)
                ):
                    omni.kit.commands.execute("SetAnimCurveKeys", paths=command_attr_path, value=usd_model.get_value())

            return True, on_click_fn, "Click to Add a Key"

        self._flag_anim_curve = cs_mgr.register_control_state(
            on_refresh_anim_curve, on_build_anim_curve, icon_anim_curve, ANIM_CURVE_CTL_STATE_PRIORITY
        )
