# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
from omni import ui

from .constant import COLORS, DarkColors, FontSize, LightColors, MouseKey
from .model import EditEventFloatModel, EditEventIntModel, EditEventStringModel
from .style import DefaultWidgetStyle, get_ui_style
from .update_event_helper import delay_execute_by_frame
from .utils import get_icon_path, merge_dicts

DARK_FONT_COLOR = 0xFFCCCCCC


class Dialog:
    __instances = []
    __dialog_counter = 0

    ICON_NONE = 0
    ICON_NOTIFICATION = 1
    ICON_QUESTION = 2
    ICON_WARN = 3
    ICON_ERROR = 4

    DEFAULT_WIDTH = 400
    DEFAULT_HEIGHT = 260
    CONTENT_RATIO = 0.66

    LIGHT_STYLE = {
        "Button.Label": {"color": LightColors.Background, "font_size": FontSize.XLarge},
        "Rectangle::dialog": {"background_color": LightColors.Background, "border_width": 0, "border_radius": 1.0},
        "Rectangle::sharp": {"background_color": LightColors.Background, "border_width": 0, "border_radius": 0.0},
        "Label::title": {"color": COLORS.CLR_D, "font_size": FontSize.XLarge},
        "Label::content": {"font_size": FontSize.XLarge},
    }
    DARK_STYLE = {
        "Button.Label": {"font_size": FontSize.XLarge},
        "Rectangle::dialog": {"background_color": DarkColors.Background, "border_width": 0, "border_radius": 1.0},
        "Rectangle::sharp": {"background_color": DarkColors.Background, "border_width": 0, "border_radius": 0.0},
        "Label::title": {"color": COLORS.CLR_8, "font_size": FontSize.XLarge},
        "Label::content": {"font_size": FontSize.XLarge},
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    @staticmethod
    def cleanup_instance(dialog):
        Dialog.__instances.remove(dialog)
        return True

    def __init__(self, title, message, icon=ICON_NONE, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        self._title = title
        self._message = message
        self._buttons = []
        self._width = width
        self._height = height
        self._callbacks = {}
        self._icons = {
            Dialog.ICON_NONE: None,
            Dialog.ICON_NOTIFICATION: self._get_icon_path("Notification.svg"),
            Dialog.ICON_QUESTION: self._get_icon_path("question.png"),
            Dialog.ICON_WARN: self._get_icon_path("warn.png"),
            Dialog.ICON_ERROR: self._get_icon_path("error.png"),
        }

        self._dialog_icon = None
        self._selected_button = None
        self._button_width = 0
        self._button_spacing = 5
        self._padding_x = self._width * (1 - Dialog.CONTENT_RATIO) / 2

        if icon in self._icons:
            self._dialog_icon = self._icons[icon]

        self._ui_style = get_ui_style()

    def add_button(self, title, is_final, callback: callable = None, image=""):
        self._buttons.append({"title": title, "is_final": is_final, "callback": callback, "image": image})

    def set_button_alignment(self, width=0, spacing=5):
        self._button_width = width
        self._button_spacing = spacing

    def show(self, is_modal, ui_style="NvidiaLight"):
        # Prevent duplicate show
        if self in Dialog.__instances:  # pragma: no cover
            # A dialog can not be show two times at same time
            carb.log_error(f"A dialog named {self._title} show again while it is already shown")
            return False
        Dialog.__instances.append(self)

        title_internal = f"[DIALOG#{Dialog.__dialog_counter} - {self._title}"
        Dialog.__dialog_counter += 1

        flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
        )
        if is_modal:
            flags |= ui.WINDOW_FLAGS_MODAL

        self._window = ui.Window(
            title_internal,
            ui.DockPreference.DISABLED,
            width=self._width,
            height=self._height,
            flags=flags,
            padding_x=0,
            padding_y=0,
        )

        x = (ui.Workspace.get_main_window_width() - Dialog.DEFAULT_WIDTH) / 2
        y = (ui.Workspace.get_main_window_height() - Dialog.DEFAULT_HEIGHT) / 2
        self._window.position_x = x
        self._window.position_y = y

        style = DefaultWidgetStyle.get_style(self._ui_style)
        style = merge_dicts(style, Dialog.UI_STYLES[ui_style])
        style = merge_dicts(style, self._get_style())
        self._window.frame.set_style(style)

        # Make sure we have at least one final button
        has_final_button = False
        for button in self._buttons:
            if button["is_final"]:
                has_final_button = True
        if not has_final_button:
            button = {"title": "Close", "is_final": True, "callback": None, "image": ""}
            self._buttons.append(button)

        with self._window.frame:
            with ui.VStack(spacing=0):
                self._build_title_bar()
                ui.Spacer(height=20)
                self._build_content()
                if self._height > 0:
                    ui.Spacer()
                else:
                    ui.Spacer(height=20)
                self._build_buttons()
                ui.Spacer(height=5)
        return True

    def _get_style(self):
        return {}

    def _build_title_bar(self):
        with ui.ZStack(height=30):
            ui.Rectangle(name="dialog")
            with ui.Placer(offset_x=0, offset_y=10):
                ui.Rectangle(name="sharp", height=20)
            if self._dialog_icon is not None:
                with ui.HStack(width=30):
                    ui.Spacer(width=3)
                    with ui.VStack():
                        ui.Spacer()
                        ui.Image(self._dialog_icon, width=24, height=24)
                        ui.Spacer()
            ui.Label(self._title, name="title", alignment=ui.Alignment.CENTER)

    def _build_content(self):
        with ui.HStack():
            ui.Spacer(width=15)
            self._msg_label = ui.Label(
                self._message, name="content", width=ui.Fraction(1), alignment=ui.Alignment.CENTER, word_wrap=True
            )
            ui.Spacer(width=15)

    def _build_buttons(self):
        button_count = len(self._buttons)
        with ui.HStack(height=24):
            if button_count > 1:
                ui.Spacer(width=self._padding_x)
                head = True
                for button in self._buttons:
                    if head:
                        head = False
                    else:
                        if self._button_spacing > 0:
                            ui.Spacer(width=self._button_spacing)
                        else:
                            ui.Spacer()
                    self._build_button(button)
                ui.Spacer(width=self._padding_x)
            else:
                ui.Spacer()
                button = self._buttons[0]
                self._build_button(button)
                ui.Spacer()
        ui.Spacer(height=20)

    def _build_button(self, button):
        ui_button = ui.Button(
            button["title"],
            image_url=button["image"],
            # image_width=self._button_width,
            image_height=24,
            name="dialog",
            height=20,
            mouse_pressed_fn=lambda x, y, key, alt, btn_pressed=button: self._on_button_clicked(key, btn_pressed),
        )

        if self._button_width > 0:
            ui_button.width = ui.Pixel(self._button_width)
        return ui_button

    def _get_icon_path(self, file):
        return get_icon_path("dialog/" + file)

    def _on_button_clicked(self, mouse_key, button):
        if mouse_key != MouseKey.LEFT:
            return

        if button["callback"]:
            result = button["callback"]()
        if button["is_final"]:
            self._final_close()

    def _final_close(self):
        self._window.visible = False
        # Free the reference, ceanup this dialog
        # Must delay called, since this event is triggered inside window drawing.
        # To release a window inside drawing, will cause crash.
        delay_execute_by_frame(1, lambda dialog=self: Dialog.cleanup_instance(dialog), "Clean up dialog instance")


class MessageDialog(Dialog):
    def __init__(self, title, message, show_after_create=True):
        super().__init__(title, message, Dialog.ICON_NOTIFICATION)

        self.add_button("Ok", True, None)

        if show_after_create:
            self.show(True)


class QuestionDialog(Dialog):
    def __init__(self, title, message, on_yes_fn, show_after_create=True, width=Dialog.DEFAULT_WIDTH, on_no_fn=None):
        super().__init__(title, message, Dialog.ICON_QUESTION, width=width)

        self.add_button("Yes", True, on_yes_fn)
        self.add_button("No", True, on_no_fn)

        if show_after_create:
            self.show(True)


class InputDialog(Dialog):
    INPUT_TYPE_NONE = -1
    INPUT_TYPE_STRING = 0
    INPUT_TYPE_INT = 1
    INPUT_TYPE_FLOAT = 2

    LIGHT_STYLE = {
        "Field": {
            "color": 0xFFDBDBDB,
            "background_color": COLORS.WIDGET_BACKGROUND_LIGHT,
            "background_selected_color": LightColors.ButtonSelected,
            "border_radius": 0,
        }
    }
    DARK_STYLE = {"Field": {"border_radius": 0}}
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self,
        title,
        input_type,
        on_finished_fn,
        default_value=None,
        prompt=None,
        check_valid_fn=None,
        on_cancelled_fn=None,
        icon=Dialog.ICON_NONE,
        width=Dialog.DEFAULT_WIDTH,
        height=Dialog.DEFAULT_HEIGHT,
        modal=True,
        show_after_create=True,
    ):
        self._input_type = input_type
        self._prompt = prompt
        self._default_value = default_value
        self._value = default_value

        self._check_valid_fn = check_valid_fn
        self._on_finished = on_finished_fn
        self._on_cancelled = on_cancelled_fn

        if self._input_type == InputDialog.INPUT_TYPE_STRING:
            self._model = EditEventStringModel(None, self._on_edit_finished, self._default_value)
        elif self._input_type == InputDialog.INPUT_TYPE_INT:
            self._model = EditEventIntModel(None, self._on_edit_finished, self._default_value)
        elif self._input_type == InputDialog.INPUT_TYPE_FLOAT:
            self._model = EditEventFloatModel(None, self._on_edit_finished, self._default_value)
            # ui.FloatField(self._model, name="input", width=self._width / 2, height=height)
        else:  # pragma: no cover
            carb.log_error(f"Invalid input type:{input_type}")
            return

        super().__init__(title, None, icon, width, height)

        self.add_button("Ok", False, lambda: self._on_close(True))
        self.add_button("Cancel", True, lambda: self._on_close(False))

        self.set_button_alignment(120, 0)

        if show_after_create:
            self.show(modal)

    # overide the baseclass' method
    def _get_style(self):
        return InputDialog.UI_STYLES[self._ui_style]

    def _build_content(self):
        width = self._width * Dialog.CONTENT_RATIO
        height = 24

        with ui.HStack():
            ui.Spacer(width=self._padding_x)
            with ui.VStack():
                if self._prompt is not None:
                    ui.Label(self._prompt, name="content", width=0, height=height, alignment=ui.Alignment.RIGHT)
                    ui.Spacer(height=10)

                with ui.HStack(height=height):
                    if self._input_type == InputDialog.INPUT_TYPE_STRING:
                        ui.StringField(self._model, name="input", height=height)
                    elif self._input_type == InputDialog.INPUT_TYPE_INT:
                        ui.IntField(self._model, name="input", height=height)
                    elif self._input_type == InputDialog.INPUT_TYPE_FLOAT:
                        ui.FloatField(self._model, name="input", height=height)
                ui.Spacer(height=10)

                self._build_custom_content()

                ui.Spacer(height=20)
                self._error_label = ui.Label("", name="content", height=height)
            ui.Spacer(width=self._padding_x)

    def _build_custom_content(self):
        pass

    def _on_edit_finished(self, *_):
        if self._input_type == InputDialog.INPUT_TYPE_STRING:
            self._value = self._model.get_value_as_string()
        elif self._input_type == InputDialog.INPUT_TYPE_INT:
            self._value = self._model.get_value_as_int()
        elif self._input_type == InputDialog.INPUT_TYPE_FLOAT:
            self._value = self._model.get_value_as_float()

        if self._check_valid_fn:
            if not self._check_valid_fn(self._value):
                # self._value = self._default_value
                # self._model.set_value(self._default_value)
                self._error_label.text = "Invalid value, please try again!"
                return False
            else:
                self._error_label.text = ""
        return True

    def _collect_results(self):
        values = []
        values.append(self._value)
        return values

    def _on_close(self, succ=True):
        if succ:
            if not self._on_edit_finished():
                return False
            values = self._collect_results()
            self._on_finished(*values)

            self._final_close()
        elif self._on_cancelled is not None:
            return self._on_cancelled()
