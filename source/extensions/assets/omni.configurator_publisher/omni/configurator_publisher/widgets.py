# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import math
import time
from functools import partial
from typing import List

import carb
import omni.client
import omni.ext
import omni.kit.menu.utils
import omni.kit.pipapi
import omni.ui as ui
import omni.usd

from .asset_validator_utils import AssetValidatorUtils
from .enums import CollectorSwitches, Phases
from .ext_utils import get_enabled_collector_extension_version
from .styles import UI_STYLES

SPEED_INV = 300
MODE_COLLECT = "collect"
MODE_UPLOAD = "upload"


class BoolSettingsModel(ui.AbstractValueModel):
    """The value model that is reimplemented in Python to watch a bool setting path"""

    def __init__(self, setting_path: str):
        super().__init__()

        self._setting_path = setting_path
        self._settings = carb.settings.get_settings()
        self._dict = carb.dictionary.get_dictionary()
        self._subscription = self._settings.subscribe_to_node_change_events(self._setting_path, self._on_change)
        self._value = self._settings.get(self._setting_path)

    def destroy(self):
        if self._subscription:
            self._settings.unsubscribe_to_change_events(self._subscription)
            self._subscription = None

    def _on_change(self, item, event_type):
        self._value = self._dict.get(item)
        self._value_changed()

    def get_value_as_bool(self):
        return self._value

    def get_value_as_string(self):
        return self._value

    def get_value_as_float(self):
        return self._value

    def get_value_as_int(self):
        return self._value

    def set_value(self, value):
        if value != self._value:
            self._settings.set(self._setting_path, value)


class UploadProgressModel(ui.AbstractValueModel):
    """An example of custom float model that can be used for progress bar"""

    def __init__(self):
        super().__init__()
        self._value = 0.0
        self._total = 0
        self._current = 0

    @property
    def total(self) -> str:
        return self._total

    @total.setter
    def total(self, value: int) -> None:

        if self._total == value:
            return
        self._total = value

    @property
    def current(self) -> str:
        return self._current

    @current.setter
    def current(self, value: int) -> None:

        if self._current == value:
            return
        self._current = value

    def reset(self):
        self._value = 0.0
        self._total = 0
        self._current = 0
        self._value_changed()

    def set_value(self, value):
        """Reimplemented set"""
        try:
            value = float(value)
        except ValueError:
            value = None
        if value != self._value:
            # Tell the widget that the model is changed
            self._value = value
            self._value_changed()

    def get_value_as_float(self):
        return self._value

    def get_value_as_string(self):
        return f"Uploading {self.current} of {self.total} bytes"


class CollectionProgressModel(UploadProgressModel):
    """An example of custom float model that can be used for progress bar"""

    def get_value_as_string(self):
        return f"Item {self.current} of {self.total}"


class Timer:
    MAX_TIMEOUT = 60 * 60 * 2  # 2 hours
    STEP = 1.0

    def __init__(self, warning_limit=1800, callback=None):
        self._start_time = None
        self._timer_task = None
        self._callback_fn = callback
        self._duration = 0
        self._warning_limit = warning_limit

    async def start(self):
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None

        self._start_time = time.time()
        self._duration = 0
        self._timer_task = asyncio.create_task(self._count())

        try:
            await self._timer_task
        except asyncio.CancelledError:
            carb.log_info(f"Cancelling task ... {self._timer_task}")
            raise
        except Exception as e:
            raise
        finally:
            self._timer_task = None

    async def _count(self):
        while self._duration < Timer.MAX_TIMEOUT:
            self._duration = time.time() - self._start_time
            if self._callback_fn:
                self._callback_fn(self._duration, should_warn=self._duration > self._warning_limit)
            await asyncio.sleep(Timer.STEP)

        carb.log_error("Timer has timed out")

    def stop(self):
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None
        self._start_time = None

    @staticmethod
    def convert_seconds_to_hms(sec):
        result = ""
        rest_sec = sec
        h = math.floor(rest_sec / 3600)
        if h > 0:
            result += str(h) + " h "
            rest_sec -= h * 3600
        m = math.floor(rest_sec / 60)
        if m > 0:
            result += str(m) + " min "
            rest_sec -= m * 60
        result += str(math.floor(rest_sec)) + " s"
        return result


class ProgressBar:
    def __init__(self) -> None:
        self._progress_stack = None
        self._progressbar = None
        self._collection_progress_model = CollectionProgressModel()
        self._upload_progress_model = UploadProgressModel()
        self._model = None
        self._timer = Timer(callback=self._update_timer_label)

        self._build_ui()

    def destroy(self) -> None:
        pass

    def _build_ui(self) -> None:
        self._progress_stack = ui.VStack(height=0, style=UI_STYLES)
        with self._progress_stack:
            with ui.HStack(height=0):
                ui.Spacer(width=5)
                self._progressbar = ui.ProgressBar(
                    self._collection_progress_model,
                )
                ui.Spacer(width=5)
            # Add timer
            with ui.HStack(height=0):
                ui.Spacer(width=5)
                self._timer_label = ui.Label("", style_type_name_override="TimeElapsedLabel")

    @property
    def visible(self) -> bool:
        return self._progress_stack.visible

    def hide(self):
        self._progress_stack.visible = False

    def show(self, mode):
        if mode == MODE_COLLECT:
            self._progressbar.model = self._collection_progress_model
        if mode == MODE_UPLOAD:
            self._progressbar.model = self._upload_progress_model
        self._progress_stack.visible = True

    def on_collect_progress(self, *args, **kwargs):
        self.show(MODE_COLLECT)
        self._collection_progress_model.total = args[1]
        self._collection_progress_model.current = args[0]
        self._collection_progress_model.set_value(float((args[0]) / args[1]))

    def start(self):
        asyncio.ensure_future(self._timer.start())

    def stop(self):
        self._timer.stop()

    def _update_timer_label(self, duration, should_warn=False):
        human_readable_time = Timer.convert_seconds_to_hms(duration)
        text = f"Time elapsed: {human_readable_time}"
        self._timer_label.style_type_name_override = "TimeElapsedLabel.Warning" if should_warn else "TimeElapsedLabel"

        self._timer_label.text = text


class InfoBar:
    def __init__(self) -> None:
        self.__info_stack = None
        self.__info_rectangle = None
        self.__info_label = None

        self._build_ui()

    def destroy(self) -> None:
        pass

    def _build_ui(self) -> None:
        self.__info_stack = ui.HStack(height=0)
        with self.__info_stack:
            ui.Spacer(width=5)
            with ui.ZStack(height=40):
                self.__info_rectangle = ui.Rectangle(
                    style={
                        "border_width": 1.0,
                        "background_color": ui.color("#1F2124"),
                        "border_color": ui.color("#1F2124"),
                    }
                )
                self.__info_label = ui.Label(
                    "", style={"color": ui.color("#CCCCCC")}, alignment=ui.Alignment.CENTER, word_wrap=True
                )
            ui.Spacer(width=5)

    @property
    def visible(self) -> bool:
        return self.__info_stack.visible

    def hide(self):
        self.__info_stack.visible = False

    def show(self, success, message):
        self.__info_stack.visible = True
        if success:
            border_color = ui.color("#76b900")
        else:
            border_color = ui.color("#CC0000")
        self.__info_rectangle.set_style(
            {"border_width": 1.0, "background_color": ui.color("#2C2C2C"), "border_color": border_color}
        )
        msg = ["SUCCESS" if success else "ERROR"]
        if message:
            msg.append(message)
        self.__info_label.text = " - ".join(msg)

    def set_info(self, text):
        self.__info_label.text = text


class StatusBar:

    def __init__(self) -> None:
        self._busy = True
        self._busy_state_track = None
        self._busy_state_label = None
        self._spacer_left = None
        self._spacer_right = None
        self._ping_pong_rectangle = None

        self._build_ui()

    def destroy(self) -> None:
        pass

    def _build_ui(self) -> None:
        with ui.HStack(height=24):
            ui.Spacer(width=5)
            with ui.ZStack(height=24):
                self._busy_state_track = ui.Rectangle(
                    name="default",
                    height=24,
                    style={
                        "border_width": 1.0,
                        "background_color": ui.color("#1F2124"),
                        "border_color": ui.color("#76b900"),
                    },
                )
                self._busy_state_label = ui.Label(
                    "Loading...", style={"color": ui.color("#CCCCCC")}, alignment=ui.Alignment.CENTER
                )
                with ui.HStack(height=24):
                    self._spacer_left = ui.Spacer(width=ui.Fraction(0))
                    self._ping_pong_rectangle = ui.Rectangle(
                        width=36,
                        style={"background_color": ui.color("#76b900"), "border_radius": 0.5},
                    )
                    self._spacer_right = ui.Spacer(width=ui.Fraction(1))
            ui.Spacer(width=5)

    async def _ping_pong(self):
        counter = 0
        while self._busy:
            await omni.kit.app.get_app().next_update_async()
            if not self._busy:
                break

            width = float(counter % SPEED_INV) / SPEED_INV

            width = width * 2
            if width > 1.0:
                width = 2.0 - width

            self._spacer_left.width = ui.Fraction(width)
            self._spacer_right.width = ui.Fraction(1.0 - width)
            counter += 1

    def _set_state_idle(self):
        self._busy = False
        self._ping_pong_rectangle.visible = False
        self._busy_state_track.visible = True

        self._busy_state_label.text = "Idle..."
        self._busy_state_track.set_style(
            {"border_width": 1.0, "background_color": ui.color("#2C2C2C"), "border_color": ui.color("#454545")}
        )

    def _set_state_busy(self, status_text="Publishing..."):
        if not self._busy:
            self._busy = True
            asyncio.ensure_future(self._ping_pong())
            self._ping_pong_rectangle.visible = True
            self._busy_state_track.visible = True
            self._busy_state_label.set_style({"color": ui.color("#CCCCCC")})
            self._busy_state_track.set_style(
                {"border_width": 1.0, "background_color": ui.color("#1F2124"), "border_color": ui.color("#76b900")}
            )

        self._busy_state_label.text = status_text


class PhaseSettingsWindow(ui.Window):
    def __init__(self, models, **kargs):
        flags = (
            ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_DOCKING
        )

        super().__init__("Phase Settings", width=600, height=0, flags=flags)
        self._models = models

        self.__build_fn()

    def destroy(self):
        self._models.clear()
        super().destroy()

    def __build_fn(self):
        with self.frame:
            with ui.VStack(spacing=5, height=0):
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    ui.Label(
                        "Collect:",
                        height=24,
                        tooltip="Collect the asset into an isolated folder, eliminating any external dependencies.\nYou may only want to do this if you intend to run other processes on the collected asset in between package and upload.",
                        width=60,
                    )
                    ui.CheckBox(
                        self._models.get(Phases.COLLECT, ui.SimpleBoolModel()),
                        tooltip="Collect the asset into an isolated folder, eliminating any external dependencies.\nYou may only want to do this if you intend to run other processes on the collected asset in between package and upload.",
                        width=20,
                    )
                    ui.Spacer(width=10)
                    ui.Label(
                        "Collect the asset into an isolated folder, eliminating any external dependencies.\nYou may only want to do this if you intend to run other processes on the collected asset in between package and upload.",
                        tooltip="Ignore unused materials.\n When this is unchecked, temp objects will be created that the unbound material will be assigned to.",
                        alignment=ui.Alignment.LEFT_CENTER,
                        word_wrap=True,
                    )
                    ui.Spacer(width=25)

                tooltip = "Validate assets against Omniverse specific rules to ensure they run smoothly."
                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    ui.Label(
                        "Validate:",
                        height=24,
                        tooltip=tooltip,
                        width=60,
                    )
                    ui.CheckBox(self._models.get(Phases.VALIDATE, ui.SimpleBoolModel()), tooltip=".", width=20)
                    ui.Spacer(width=10)
                    ui.Label(
                        tooltip,
                        height=12,
                        width=800,
                    )
                    ui.Spacer(width=25)

                tooltip = "Optimize scene to reduce stage size and speed up stage loading."
                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    ui.Label(
                        "Optimize:",
                        height=24,
                        tooltip=tooltip,
                        width=60,
                    )
                    ui.CheckBox(self._models.get(Phases.OPTIMIZE, ui.SimpleBoolModel()), tooltip=".", width=20)
                    ui.Spacer(width=10)
                    ui.Label(
                        tooltip,
                        height=12,
                        width=800,
                    )
                    ui.Spacer(width=25)

                tooltip = "Generate UJITSO Cache to speed up stage loading."
                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    ui.Label(
                        "Cache:",
                        height=24,
                        tooltip=tooltip,
                        width=60,
                    )
                    ui.CheckBox(self._models.get(Phases.CACHE, ui.SimpleBoolModel()), tooltip=".", width=20)
                    ui.Spacer(width=10)
                    ui.Label(tooltip, height=12, alignment=ui.Alignment.LEFT_CENTER, word_wrap=True)
                    ui.Spacer(width=25)
                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    ui.Label(
                        "Package:",
                        height=24,
                        tooltip="Package collected asset folder.",
                        width=60,
                    )
                    ui.CheckBox(
                        self._models.get(Phases.PACKAGE, ui.SimpleBoolModel()),
                        tooltip="Package collected asset folder.",
                        width=20,
                    )
                    ui.Spacer(width=10)
                    ui.Label(
                        "Package collected asset folder.",
                        tooltip="Package collected asset folder.",
                        alignment=ui.Alignment.LEFT_CENTER,
                        word_wrap=True,
                    )
                    ui.Spacer(width=25)
                # with ui.HStack(height=0):
                #     ui.Spacer(width=5)
                #     ui.Label(
                #         "Upload:",
                #         height=24,
                #         tooltip="Upload the Zip to GDN",
                #         width=60,
                #     )
                #     self._perform_upload_cb = ui.CheckBox(self._models.get(Phases.UPLOAD, ui.SimpleBoolModel()),
                #                                           tooltip="Upload the Zip to GDN", width=20)
                #     ui.Spacer(width=10)
                #     ui.Label(
                #         "Upload the Zip to GDN", height=12,
                #         tooltip="Upload the Zip to GDN", word_wrap=True,
                #         alignment=ui.Alignment.LEFT_CENTER)
                #     ui.Spacer(width=25)

                ui.Spacer(height=10)


class PhasesWidget:
    def __init__(self, models) -> None:
        self._models = models
        self._phase_labels = {}

        self._build_ui()

    def destroy(self) -> None:
        self._phase_labels = None
        self._models = None

    def _build_ui(self) -> None:
        counter = 0
        with ui.HStack(height=25, tooltip="The active phases to be ran on publish.", style=UI_STYLES):
            ui.Spacer()

            for phase, model in self._models.items():
                with ui.ZStack(width=0):
                    label = ui.Label(
                        phase.value.capitalize(),
                        style_type_name_override="PhaseLabel",
                        alignment=ui.Alignment.CENTER,
                        width=25,
                        spacing=0,
                    )
                    button = ui.InvisibleButton()
                    button.set_clicked_fn(partial(self._on_phase_clicked, phase.value))
                self._phase_labels[phase] = label
                model.add_value_changed_fn(partial(self._on_phase_changed, label))
                model._value_changed()
                counter += 1
                if counter > len(self._models) - 1:
                    break
                ui.Label("|", style_type_name_override="PhaseLabel", alignment=ui.Alignment.CENTER, width=15)
            ui.Spacer()

    def _on_phase_changed(self, label, model):
        label.style_type_name_override = "PhaseLabel" if model.get_value_as_bool() else "PhaseLabel.Disabled"

    def _on_phase_clicked(self, phase):
        setting_path = f"persistent/configurator_publisher/{phase}"
        settings = carb.settings.get_settings()
        value = settings.get(setting_path)
        settings.set(setting_path, not value)


class CollectorSettingsWindow(ui.Window):
    def __init__(self, models, **kargs):
        flags = (
            ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_DOCKING
        )

        super().__init__("Collector Settings", width=600, height=0, flags=flags)
        self._models = models
        self.__build_fn()

    def destroy(self):
        self._models.clear()
        super().destroy()

    def __build_fn(self):
        collector_version = get_enabled_collector_extension_version()

        with self.frame:
            with ui.VStack(spacing=5, height=0):
                ui.Spacer(height=10)
                if collector_version >= (2, 2, 12):
                    with ui.HStack(height=0):
                        ui.Spacer(width=5)
                        tooltip = "Convert ascii usd (USDA) to binary USD (USDC) format."
                        ui.Label("Ascii to Binary:", height=24, width=120)
                        self._perform_collect_cb = ui.CheckBox(
                            self._models.get(CollectorSwitches.ASCII_TO_BINARY, ui.SimpleBoolModel()), width=20
                        )
                        ui.Spacer(width=10)
                        ui.Label(tooltip, height=12, word_wrap=True, alignment=ui.Alignment.LEFT_CENTER)
                        ui.Spacer(width=25)

                if collector_version >= (2, 2, 11):
                    with ui.HStack(height=0):
                        ui.Spacer(width=5)
                        tooltip = "Collect default prim only for all layers."
                        ui.Label("Default Prim Only:", height=24, width=120)
                        self._perform_collect_cb = ui.CheckBox(
                            self._models.get(CollectorSwitches.DEFAULT_PRIM_ONLY, ui.SimpleBoolModel()), width=20
                        )
                        ui.Spacer(width=10)
                        ui.Label(tooltip, height=12, word_wrap=True, alignment=ui.Alignment.LEFT_CENTER)
                        ui.Spacer(width=25)

                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    tooltip = "Flat Collection. When this option is enabled, it will use flattened folder structure."
                    ui.Label("Flat Collection:", height=24, width=120)
                    self._perform_collect_cb = ui.CheckBox(
                        self._models.get(CollectorSwitches.FLAT_COLLECTION, ui.SimpleBoolModel()), width=20
                    )
                    ui.Spacer(width=10)
                    ui.Label(tooltip, height=12, word_wrap=True, alignment=ui.Alignment.LEFT_CENTER)
                    ui.Spacer(width=25)
                ui.Spacer(height=10)


class ValidatorSettingsModel:
    def __init__(self):
        self.__models = {}
        for category in AssetValidatorUtils.get_all_categories():
            rules = AssetValidatorUtils.get_rules_of_category(category)
            self.__models[category] = {
                r: BoolSettingsModel(AssetValidatorUtils.get_rule_setting_path(r)) for r in rules
            }

    def destroy(self):
        self.__models = {}

    def get_rule_models_of_category(self, category: str):
        return self.__models.get(category, {})

    def get_enabled_categories_and_rules(self):
        """
        It returns whole category if all rules in that category are enabled, and single rules for
        those categories that are not fully enabled.
        """

        enabled_categories = []
        enabled_rules = []
        for category, rule_models in self.__models.items():
            all_rules_enabled = all(model.get_value_as_bool() for model in rule_models.values())
            if all_rules_enabled:
                enabled_categories.append(category)
            else:
                rules = [name for (name, model) in rule_models.items() if model.get_value_as_bool()]
                enabled_rules.extend(rules)

        return enabled_categories, enabled_rules


class ValidatorCategoryFrame(ui.CollapsableFrame):
    def __init__(self, category: str, validator_setting_model: ValidatorSettingsModel, **kwargs):
        super().__init__(category, **kwargs)

        self.__validator_setting_model = validator_setting_model
        self.__category = category

        with self:
            self.__build_fn()

    def destroy(self):
        super().destroy()
        self.__validator_setting_model = None

    @property
    def category(self) -> str:
        return self.__category

    def __build_fn(self):
        rule_models = self.__validator_setting_model.get_rule_models_of_category(self.__category)
        with ui.VStack(spacing=5, height=0):
            for rule, model in rule_models.items():
                with ui.HStack():
                    ui.Spacer(width=5)
                    self._perform_collect_cb = ui.CheckBox(model, width=20)
                    ui.Spacer(width=5)
                    ui.Label(rule, width=260, height=0)
                    ui.Spacer(width=10)
                    description = AssetValidatorUtils.get_rule_description(rule)
                    description = description.strip(" \n\r")
                    ui.Label(description, height=0, word_wrap=True, alignment=ui.Alignment.LEFT_CENTER)


class ValidatorSettingsWindow(ui.Window):
    def __init__(self, validator_setting_model):
        flags = ui.WINDOW_FLAGS_NO_COLLAPSE | ui.WINDOW_FLAGS_NO_DOCKING

        super().__init__("Validator Settings", width=1000, height=600, flags=flags)
        self.__all_frames = []
        self.__build_fn(validator_setting_model)

    def destroy(self):
        super().destroy()

        for frame in self.__all_frames:
            frame.destroy()

    def __build_fn(self, validator_setting_model):
        with self.frame:
            with ui.VStack(spacing=5):
                with ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    style_type_name_override="TreeView",
                ):
                    with ui.VStack(spacing=5):
                        for category in AssetValidatorUtils.get_all_categories():
                            self.__all_frames = [ValidatorCategoryFrame(category, validator_setting_model, height=0)]
