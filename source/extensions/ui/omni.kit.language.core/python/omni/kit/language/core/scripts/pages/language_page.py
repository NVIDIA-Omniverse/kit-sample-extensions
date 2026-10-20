# Copyright (c) 2023-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import os
from functools import partial

import carb.settings
import omni.kit.app
import omni.kit.language.core
import omni.kit.ui
import omni.ui as ui
from omni.kit.window.preferences import PreferenceBuilder, SettingType

PERSISTENT_SETTINGS_PREFIX = "/persistent"


class LanguagePreferences(PreferenceBuilder):
    def __init__(self):
        super().__init__("Language")

        self._custom_language_setting = PERSISTENT_SETTINGS_PREFIX + "/app/locale_id"
        self._language_setting = "/app/locale_id"

        self._shutdown_sub = None
        self._language_sub = omni.kit.app.SettingChangeSubscription(
            self._custom_language_setting, self._on_language_changed
        )

    def _on_language_changed(self, value: str, event_type: carb.settings.ChangeEventType):
        from omni.kit.window.popup_dialog import MessageDialog

        async def on_ok_clicked(dialog):  # pragma: no cover
            import sys

            import carb.events
            import omni.kit.app

            dialog.hide()

            def on_event(e: carb.events.IEvent):
                if e.type == omni.kit.app.PRE_SHUTDOWN_EVENT_TYPE:
                    if hasattr(omni.kit.window.preferences, "restart_kit"):
                        from omni.kit.window.preferences import restart_kit

                        restart_kit(sys.argv)
                    else:

                        def run_process(args):
                            import platform
                            import subprocess

                            kwargs = {"close_fds": False}
                            if platform.system().lower() == "windows":
                                kwargs["creationflags"] = (
                                    subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
                                )
                            subprocess.Popen(args, **kwargs)  # pylint: disable=consider-using-with

                        run_process(sys.argv)

            if not self._shutdown_sub:
                self._shutdown_sub = (
                    omni.kit.app.get_app()
                    .get_shutdown_event_stream()
                    .create_subscription_to_pop(on_event, name="language re-start", order=0)
                )
                await omni.kit.app.get_app().next_update_async()
                omni.kit.app.get_app().post_quit()

        async def on_cancel_clicked(dialog):  # pragma: no cover
            dialog.hide()
            omni.kit.window.preferences.rebuild_pages()

        if event_type == carb.settings.ChangeEventType.CHANGED:
            import omni.kit.language.core

            # is value different to locale_id_default and has language font changed and kit needs to be restarted
            if omni.kit.language.core.get_default_locale_id() == str(
                value
            ) or not omni.kit.language.core.has_font_changed(str(value)):
                omni.kit.window.preferences.rebuild_pages()
                return

            try:
                import omni.usd

                if omni.usd.get_context().has_pending_edit():  # pragma: no cover
                    dialog = MessageDialog(
                        title=f"{omni.kit.ui.get_custom_glyph_code('${glyphs}/exclamation.svg')} Language changed",
                        width=400,
                        message=f"This application will restart to apply new language.\n\nYou will be prompted to save any unsaved changes.",
                        ok_handler=lambda dialog: asyncio.ensure_future(on_ok_clicked(dialog)),
                        cancel_handler=lambda dialog: asyncio.ensure_future(on_cancel_clicked(dialog)),
                        ok_label="Continue",
                        cancel_label="Cancel",
                    )
                else:  # pragma: no cover
                    dialog = MessageDialog(
                        title=f"{omni.kit.ui.get_custom_glyph_code('${glyphs}/exclamation.svg')} Language changed",
                        width=400,
                        message=f"This application will restart to apply new language.",
                        ok_handler=lambda dialog: asyncio.ensure_future(on_ok_clicked(dialog)),
                        cancel_handler=lambda dialog: asyncio.ensure_future(on_cancel_clicked(dialog)),
                        ok_label="Restart",
                        cancel_label="Cancel",
                    )
                dialog.show()
            except ModuleNotFoundError:
                pass

    def build(self):
        """Language"""
        with ui.VStack(height=0):
            with self.add_frame("Language"):
                with ui.VStack():
                    self.create_setting_widget_combo(
                        "Locale Name (requires app restart)",
                        self._custom_language_setting,
                        list(omni.kit.language.core.get_locales()),
                    )

                    locale_id = omni.kit.language.core.get_locale_id()
                    locale_info = omni.kit.language.core.get_language_info(locale_id)
                    if locale_info:
                        lang = f"{locale_info['language_name_localized']}"
                        if locale_info["language_name_localized"] != locale_info["language_name"]:
                            lang = f"{locale_info['language_name_localized']} ({locale_info['language_name']})"

                        ui.Spacer(height=20)
                        ui.Label(f"Locale: {locale_id}", name="title", height=0, style={"font_size": 18})
                        ui.Label(f"Language: {lang}", name="title", height=0, style={"font_size": 18})
                        if locale_info["font_path"]:
                            ui.Label(
                                f"Font: {os.path.basename(locale_info['font_path'])}",
                                name="title",
                                height=0,
                                style={"font_size": 18},
                            )
                        ui.Label(f"Scale: {locale_info['font_scale']}", name="title", height=0, style={"font_size": 18})
                        ui.Spacer(height=10)
                        if locale_info["pangram"]:
                            ui.Label(
                                locale_info["pangram"], name="title", height=0, style={"font_size": 24}, word_wrap=True
                            )
                        ui.Spacer(height=10)
