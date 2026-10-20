from enum import auto

import omni.kit.app
import omni.kit.menu.utils
import omni.kit.undo
import omni.usd
from omni import ui
from omni.kit.menu.utils import MenuItemDescription


class SimplificationMenu:
    MENU_PATH = "Tools/Animation/Curve Processing/Simplify Curve"
    DEFAULT_MAX_ERROR = 5.0
    DEFAULT_COMPUTE_TANGENTS = True
    DEFAULT_AUTO_APPLY = True

    def __init__(self):
        # Register menu via omni.kit.menu.utils under Tools/Animation/Curve Processing
        self._menu_items = [
            MenuItemDescription(
                name="Animation",
                sub_menu=[
                    MenuItemDescription(
                        name="Curve Processing",
                        sub_menu=[MenuItemDescription(name="Simplify Curve", onclick_fn=self._show_menu)],
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_items, "Tools", 0, True)

        self._attribute_names = [
            "All",
            "Position (xformOp:translate)",
            "Rotation (xformOp:rotateXYZ)",
            "Scale (xformOp:scale)",
            "Visibility (visibility)",
        ]
        self._attribute_strings = ["", "xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale", "visibility"]
        self._stage_sub = omni.usd.get_context().get_stage_event_stream().create_subscription_to_pop(self._on_stage)
        self._prim_indicator = None
        self._window_error = None
        error_window_title = "Error"
        unique_postfix = "###Simplification Menu"
        self._error_window_title = error_window_title + unique_postfix

    def __del__(self):
        self.destory()

    def destory(self):
        # Unregister menu items
        try:
            if hasattr(self, "_menu_items") and self._menu_items:
                omni.kit.menu.utils.remove_menu_items(self._menu_items, "Tools")
        finally:
            self._menu_items = None

        self._error_slider = None
        self._compute_tangents_checkbox = None
        self._attribute_combo = None
        self._apply_on_change = None
        self._apply_button = None
        self._cancel_button = None
        self._close_error_window_button = None
        self._window = None
        if self._window_error is not None:
            self._window_error.destroy()
        self._window_error = None
        self._stage_sub = None

    def _show_menu(self, *args, **kwargs):
        self._processed = None
        self._window = ui.Window("Animation Curve Simplification", width=480, height=260)
        with self._window.frame:
            with ui.VStack():
                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label(
                        "Target Prim(s)",
                    )
                    self._prim_indicator = ui.StringField(
                        read_only=True,
                    )
                    self._prim_indicator.model.set_value(
                        ", ".join(omni.usd.get_context().get_selection().get_selected_prim_paths())
                    )
                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label("Apply on parameter change")
                    self._apply_on_change = ui.CheckBox(
                        tooltip="Simplification is applied when any parameter of this menu is changed"
                    )
                    self._apply_on_change.model.set_value(self.DEFAULT_AUTO_APPLY)

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label("Error tolerance (%)")
                    self._error_slider = ui.FloatSlider(
                        min=0.0, max=20.0, tooltip="Maximum allowed error (approximately) for continuous data"
                    )
                    self._error_slider.model.set_value(self.DEFAULT_MAX_ERROR)
                    self._error_slider.model.add_value_changed_fn(self._parameter_changed)

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label("Sharp tangents")
                    self._compute_tangents_checkbox = ui.CheckBox(
                        tooltip="Compute tangents for sparse curve from dense input keys"
                    )
                    self._compute_tangents_checkbox.model.set_value(self.DEFAULT_COMPUTE_TANGENTS)
                    self._compute_tangents_checkbox.model.add_value_changed_fn(self._parameter_changed)

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label("Attribute")
                    self._attribute_combo = ui.ComboBox(
                        False,
                        *self._attribute_names,
                        tooltip="Attribute to convert",
                    )

                ui.Spacer()
                with ui.HStack():
                    self._apply_button = ui.Button("Apply", height=30, clicked_fn=lambda: self._apply(True))
                    self._cancel_button = ui.Button("Cancel", height=30, clicked_fn=self._cancel)

                ui.Spacer()

    def _parameter_changed(self, value):
        auto_apply = self._apply_on_change.model.get_value_as_bool()
        if self._processed is not None or auto_apply:
            self._apply(False)

    def _cancel(self):
        if self._processed is not None:
            omni.kit.undo.undo()
        self._window.visible = False

    def _apply(self, exit: bool = True):
        context = omni.usd.get_context()
        self._paths = None
        if context:
            selection = context.get_selection()
            if selection:
                self._paths = selection.get_selected_prim_paths()

        if self._paths is None or type(self._paths) is not list or len(self._paths) == 0:
            self._show_error("Please select a prim!")
            return

        if self._processed == self._paths:
            omni.kit.undo.undo()

        max_error = self._error_slider.model.get_value_as_float()
        compute_tangents = self._compute_tangents_checkbox.model.get_value_as_bool()

        attribute_to_process = self._attribute_strings[self._attribute_combo.model.get_item_value_model().as_int]

        if len(attribute_to_process) == 0:
            attribute_to_process = None  # Command expects a None to process all attributes

        omni.kit.commands.execute(
            "SimplifyAnimCurves",
            attribute_mask=attribute_to_process,
            max_error_percent=max_error,
            compute_tangents=compute_tangents,
        )

        self._processed = self._paths
        if exit:
            self._window.visible = False

    def _show_error(self, message: str):
        if self._window_error is None:
            self._window_error = ui.Window(self._error_window_title, width=200, height=100)
            with self._window_error.frame:
                with ui.VStack():
                    self._error_msg_label = ui.Label(message)

                    def close():
                        self._window_error.visible = False

                    self._close_error_window_button = ui.Button("Close", clicked_fn=close)
        else:
            self._error_msg_label.text = message
            self._window_error.visible = True

    def _on_selection_changed(self):
        if self._prim_indicator is not None:
            self._prim_indicator.model.set_value(
                ", ".join(omni.usd.get_context().get_selection().get_selected_prim_paths())
            )

    def _on_stage(self, stage_event):
        if stage_event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self._on_selection_changed()
