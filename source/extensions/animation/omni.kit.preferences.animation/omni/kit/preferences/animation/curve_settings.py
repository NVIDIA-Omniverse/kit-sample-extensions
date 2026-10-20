import carb.settings
from omni import ui
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX, PreferenceBuilder, SettingType

CURVE_SETTINGS_TITLE = "Curve Settings"

DELETE_EMPTY_CURVE_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/app/omni.anim.curve.core/deleteEmptyCurve"
AUTO_KEY_ALL_XFORM_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/app/anim/autoKeyAllXform"
AUTO_KEY_ALL_XFORM_SETTING_DEFAULT = False
DEFAULT_TANGENT_TYPE_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentType"
DEFAULT_TANGENT_WEIGHTED_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentWeighted"
DEFAULT_TANGENT_BROKEN_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentBroken"
DEFAULT_TANGENT_PRE_INFINITY_TYPE_SETTING = (
    f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentPreInfinity"
)
DEFAULT_TANGENT_POST_INFINITY_TYPE_SETTING = (
    f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentPostInfinity"
)

DefaultTangentTypeSettingTokens = ["auto", "smooth", "flat", "linear", "step"]  # intentionally no "fixed"
DefaultInfinityTypeSettingTokens = ["constant", "cycle", "cycleRelative", "linear", "oscillate"]

_g_settings = carb.settings.get_settings()


def build_curve_preferences(pref_builder: PreferenceBuilder):
    with ui.VStack():
        if _g_settings.get(AUTO_KEY_ALL_XFORM_SETTING) is None:
            _g_settings.set_default_bool(AUTO_KEY_ALL_XFORM_SETTING, AUTO_KEY_ALL_XFORM_SETTING_DEFAULT)
        pref_builder.create_setting_widget(
            "AutoKey All Transforms",
            AUTO_KEY_ALL_XFORM_SETTING,
            SettingType.BOOL,
            tooltip="Toggle the auto animation key authoring feature",
        )

        if _g_settings.get(DEFAULT_TANGENT_TYPE_SETTING) is None:
            _g_settings.set(DEFAULT_TANGENT_TYPE_SETTING, DefaultTangentTypeSettingTokens[0])
        pref_builder.create_setting_widget_combo(
            "Default Tangent Type", DEFAULT_TANGENT_TYPE_SETTING, DefaultTangentTypeSettingTokens
        )

        if _g_settings.get(DEFAULT_TANGENT_WEIGHTED_SETTING) is None:
            _g_settings.set_default_bool(DEFAULT_TANGENT_WEIGHTED_SETTING, False)
        pref_builder.create_setting_widget(
            "Weighted Tangent by Default", DEFAULT_TANGENT_WEIGHTED_SETTING, SettingType.BOOL
        )

        if _g_settings.get(DEFAULT_TANGENT_BROKEN_SETTING) is None:
            _g_settings.set_default_bool(DEFAULT_TANGENT_BROKEN_SETTING, False)
        pref_builder.create_setting_widget(
            "Broken Tangent by Default", DEFAULT_TANGENT_BROKEN_SETTING, SettingType.BOOL
        )

        if _g_settings.get(DEFAULT_TANGENT_PRE_INFINITY_TYPE_SETTING) is None:
            _g_settings.set(DEFAULT_TANGENT_PRE_INFINITY_TYPE_SETTING, DefaultInfinityTypeSettingTokens[0])
        pref_builder.create_setting_widget_combo(
            "Default Pre-Infinity Type", DEFAULT_TANGENT_PRE_INFINITY_TYPE_SETTING, DefaultInfinityTypeSettingTokens
        )

        if _g_settings.get(DEFAULT_TANGENT_POST_INFINITY_TYPE_SETTING) is None:
            _g_settings.set(DEFAULT_TANGENT_POST_INFINITY_TYPE_SETTING, DefaultInfinityTypeSettingTokens[0])
        pref_builder.create_setting_widget_combo(
            "Default Post-Infinity Type", DEFAULT_TANGENT_POST_INFINITY_TYPE_SETTING, DefaultInfinityTypeSettingTokens
        )

        if _g_settings.get(DELETE_EMPTY_CURVE_SETTING) is None:
            _g_settings.set_default_bool(DELETE_EMPTY_CURVE_SETTING, True)
        pref_builder.create_setting_widget(
            "Delete Empty Curve",
            DELETE_EMPTY_CURVE_SETTING,
            SettingType.BOOL,
            tooltip="Toggle whether a curve is deleted when the last key is deleted.",
        )

        ui.Button("Run Backwards Compatibility on Folder", width=400, clicked_fn=run_backwards_compatibility)


def get_auto_key_all_xform() -> bool:
    auto_key_all_xform = _g_settings.get_as_bool(AUTO_KEY_ALL_XFORM_SETTING)
    if auto_key_all_xform == None:
        # fallback to default if setting not found
        auto_key_all_xform = AUTO_KEY_ALL_XFORM_SETTING_DEFAULT

    return auto_key_all_xform


def set_auto_key_all_xform(value: bool):
    return _g_settings.set(AUTO_KEY_ALL_XFORM_SETTING, value)


def run_backwards_compatibility():
    import asyncio
    import os.path
    import threading
    import time

    import AnimationSchema
    import omni.kit.app
    import omni.kit.widget.prompt
    from omni.kit.window.filepicker import FilePickerDialog
    from pxr import Tf, Usd

    # Iterates a folder
    stopped = False
    errors = []
    prompt: omni.kit.widget.prompt.Prompt = None
    upgraded_files = []

    async def for_each_file(dirpath, callable):
        prompt.set_text(f"Processing folder {dirpath}")

        result = await omni.client.list_async(dirpath)
        if result[0] != omni.client.Result.OK:
            errors.append(f"Can't list content of {dirpath}")
            return

        folders = []
        files = []

        for entry in result[1]:
            full_path = f"{dirpath}/{entry.relative_path}"
            is_folder = (entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN) > 0
            if is_folder:
                folders.append(full_path)
            else:
                files.append(full_path)

        for file in files:
            if stopped:
                return

            await callable(file)

        for folder in folders:
            if stopped:
                return

            await for_each_file(folder, callable)

    # Upgrades a USD file
    async def upgrade_usd(path):
        local_errors = []

        def do_upgrading():
            nonlocal local_errors

            try:
                stage = Usd.Stage.Open(path)

                upgraded = False

                for prim in stage.Traverse():
                    if prim.GetTypeName() != "OmniGraphNode":
                        continue

                    node_type = prim.GetAttribute("node:type").Get()
                    version_attr = prim.GetAttribute("node:typeVersion")

                    if node_type == "omni.anim.curve.core.AnimCurve":
                        if version_attr.Get() < 2:
                            local_errors.append(
                                f"Prim {prim.GetPath()} in stage {path} is too old, it can't be batched upgraded."
                            )
                            continue

                        if version_attr.Get() >= 5:
                            continue

                        version_attr.Set(5)

                        upgraded = True

                        rel = prim.GetRelationship("inputs:AnimData")
                        if not rel:
                            continue

                        rel.SetHidden(True)

                        anim_data_paths = rel.GetTargets()
                        if not anim_data_paths:
                            continue

                        anim_data_path = anim_data_paths[0]

                    elif node_type == "omni.anim.Timeline":
                        if version_attr.Get() >= 2:
                            continue

                        version_attr.Set(2)

                        upgraded = True

                        anim_data_path = prim.GetPath().AppendChild("animationData")
                    else:
                        continue

                    anim_data_prim = stage.GetPrimAtPath(anim_data_path)

                    curve_api = AnimationSchema.AnimationCurveAPI(anim_data_prim)
                    if not curve_api:
                        continue

                    curve_names = curve_api.GetCurves()
                    for curve_name in curve_names:
                        for prop in anim_data_prim.GetAuthoredPropertiesInNamespace(curve_name):
                            prop.FlattenTo(prim)

                stage.Save()

                if upgraded:
                    upgraded_files.append(path)

            except Exception as excpt:
                local_errors.append(str(excpt))

        thread = threading.Thread(target=do_upgrading)
        thread.start()
        while thread.is_alive():
            await omni.kit.app.get_app().next_update_async()

        errors.extend(local_errors)

    # Does the upgrading for a file
    async def handle_file(path):
        if not os.path.splitext(path)[1] in [".usd", ".usda", ".usdc", ".usdz"]:
            prompt.set_text(f"Skipped file {path}")
            return

        prompt.set_text(f"Upgrading file {path}")

        await upgrade_usd(path)

        prompt.set_text(f"Upgraded file {path}")

        await omni.kit.app.get_app().next_update_async()

    # Does upgrading for a folder
    async def run_backwards_compatibility_async(folder):
        carb.log_info("Curve animation: Running backwards compatibility on " + folder)

        def on_stop_bn():
            nonlocal stopped
            stopped = True
            errors.append("Upgrading is stopped by user.")

        nonlocal prompt
        title = "Curve Animation Backwards Compatibility"
        prompt = omni.kit.widget.prompt.Prompt(title, "", "Stop", ok_button_fn=on_stop_bn)
        prompt._window.flags = prompt._window.flags & ~ui.WINDOW_FLAGS_NO_MOVE & ~ui.WINDOW_FLAGS_NO_RESIZE
        prompt.show()

        await for_each_file(folder, handle_file)

        for error in errors:
            carb.log_error(f"Curve Animation Compatibility: {error}")

        for path in upgraded_files:
            carb.log_warn(f"Curve Animation Compatibility: Upgraded file {path}")

        prompt.destroy()

        text = f"Upgraded {len(upgraded_files)} files. "
        if errors:
            text += "Upgrading is completed with errors. Check log for details."
        else:
            text += "Upgrading is completed. Check log for details."

        finished_prompt = omni.kit.widget.prompt.Prompt(title, text, modal=True)
        finished_prompt.show()

        carb.log_info("Curve animation: Finished backwards compatibility on " + folder)

    # Choose a fold and does upgrading
    def on_choose(fp_dialog, filename, dirpath):
        asyncio.ensure_future(run_backwards_compatibility_async(dirpath))
        fp_dialog.hide()

        async def destroy_dlg():
            fp_dialog.destroy()

        asyncio.ensure_future(destroy_dlg())

    item_filter_options = ["USD Files (*.usd, *.usda, *.usdc, *.usdz)", "All Files (*)"]
    fp_dialog = FilePickerDialog(
        "Choose Folder",
        apply_button_label="Choose",
        click_apply_handler=lambda filename, dirname: on_choose(fp_dialog, filename, dirname),
        item_filter_options=item_filter_options,
    )

    fp_dialog.show(None)
