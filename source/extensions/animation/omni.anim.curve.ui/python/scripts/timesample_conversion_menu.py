import omni.kit.app
import omni.kit.menu.utils
import omni.usd
from omni import ui
from omni.kit.menu.utils import MenuItemDescription


class TimesampleConversionMenu:
    MENU_PATH = "Tools/Animation/Convert/USD TimeSample to Curves"
    DEFAULT_START_TIME = 0.0
    DEFAULT_MAX_ERROR = 1.0
    DEFAULT_APPLY_SPARSE = True
    DEFAULT_COMPUTE_TANGENTS = True

    def __init__(self):
        # Register menu via omni.kit.menu.utils under Tools/Animation/Convert
        self._menu_items = [
            MenuItemDescription(
                name="Animation",
                sub_menu=[
                    MenuItemDescription(
                        name="Convert",
                        sub_menu=[MenuItemDescription(name="USD TimeSample to Curves", onclick_fn=self._show_menu)],
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_items, "Tools", 0, True)

        self._fps_strings = ["From timeline", "24.00 FPS", "29.97 FPS", "30.00 FPS", "60.00 FPS", "120.00 FPS"]
        self._fps_values = [0, 24.0, 29.97, 30.0, 60.0, 120.0]

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
        unique_postfix = "###Timesample Conversion Menu"
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

        self._fps_combo = None
        self._start_time_field = None
        self._sparse_checkbox = None
        self._error_slider = None
        self._compute_tangents_checkbox = None
        self._attribute_combo = None
        self._apply_button = None
        self._close_error_window_button = None
        self._window = None
        if self._window_error is not None:
            self._window_error.destroy()
        self._window_error = None
        self._stage_sub = None

    def _show_menu(self, *args, **kwargs):
        self._window = ui.Window("USD TimeSample to Curves", width=500, height=300)
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
                    ui.Label(
                        "Start Frame Offset",
                        tooltip="Enter an offset value for the animation curves start time.",
                    )
                    self._start_time_field = ui.FloatField()
                    self._start_time_field.model.set_value(self.DEFAULT_START_TIME)

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label(
                        "FPS",
                        tooltip="Set output Frames per second.",
                    )
                    self._fps_combo = ui.ComboBox(
                        False,
                        *self._fps_strings,
                    )

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label(
                        "Attributes",
                        tooltip="Set which animateable attributes you'd like to convert.",
                    )
                    self._attribute_combo = ui.ComboBox(
                        False,
                        *self._attribute_names,
                    )

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label(
                        "Sparse Curve",
                        tooltip="Sparse Curve - allows the user to reduce the number of keys that define a curve "
                        "shape while maintaining the original motion fidelity. Useful to reduce baked "
                        "animations to editable curves.",
                    )
                    self._sparse_checkbox = ui.CheckBox()
                    self._sparse_checkbox.model.set_value(self.DEFAULT_APPLY_SPARSE)

                    def _toggle_sparse(model):
                        apply_simplification = model.get_value_as_bool()
                        self._error_slider.enabled = self._compute_tangents_checkbox.enabled = apply_simplification

                    self._sparse_checkbox.model.add_value_changed_fn(_toggle_sparse)

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label(
                        "\tError tolerance (%)",
                        tooltip="Maximum allowed error (approximately) during curve simplification for continuous data.",
                    )
                    self._error_slider = ui.FloatSlider(
                        min=0.0,
                        max=20.0,
                    )
                    self._error_slider.model.set_value(self.DEFAULT_MAX_ERROR)

                ui.Spacer()
                with ui.HStack(height=20):
                    ui.Label(
                        "\tTangents from samples",
                        tooltip="When Checked on - Tangents from Samples extrapolates the tangent angles from the "
                        "position of neighbouring keys.",
                    )
                    self._compute_tangents_checkbox = ui.CheckBox()
                    self._compute_tangents_checkbox.model.set_value(self.DEFAULT_COMPUTE_TANGENTS)

                ui.Spacer()
                self._apply_button = ui.Button("Convert", height=30, clicked_fn=self._apply)

                ui.Spacer()

    def _apply(self):
        context = omni.usd.get_context()
        self._paths = None
        if context:
            selection = context.get_selection()
            if selection:
                self._paths = selection.get_selected_prim_paths()

        if self._paths is None or type(self._paths) is not list or len(self._paths) == 0:
            self._show_error("Please select a prim!")
            return

        source_fps = self._fps_values[self._fps_combo.model.get_item_value_model().as_int]
        start_time = self._start_time_field.model.get_value_as_float()

        apply_simplification = self._sparse_checkbox.model.get_value_as_bool()
        max_error = self._error_slider.model.get_value_as_float()
        compute_tangents = self._compute_tangents_checkbox.model.get_value_as_bool()

        attribute_to_process = self._attribute_strings[self._attribute_combo.model.get_item_value_model().as_int]

        # TODO: show a warning in a window if the selected prims already have curves and we are about to override it

        if len(attribute_to_process) == 0:
            attribute_to_process = None  # Command expects a None to process all attributes

        omni.kit.commands.execute(
            "ExtractAnimCurves",
            recursive=False,
            attribute_mask=attribute_to_process,
            source_frame_rate=source_fps,
            start_time=start_time,
            sparse=apply_simplification,
            max_error_percent=max_error,
            compute_tangents=compute_tangents,
        )
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
