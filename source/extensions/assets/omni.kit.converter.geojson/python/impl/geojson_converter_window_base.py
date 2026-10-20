import os
from typing import Any, Callable, Dict, List

import omni.usd
from omni import ui
from omni.kit.widgets.custom import TitleWindowBase  # added in config/extension.toml

from .geojson_helper import GeoJSONHelper  # from helper module and class

WINDOW_TITLE = "GeoJSON Converter (beta)"


class GeoJSONWindow(TitleWindowBase):
    def __init__(self):
        self._geojson_helper = GeoJSONHelper()  # this does not initialize helper until user enables ext
        self._usd_context = omni.usd.get_context()  # helper class gets current stage url (string in Py; char[] in C++)
        # can use stage in C++ code
        #
        enable_option = False  #
        enable_help = False
        icon = None
        super().__init__(  # defines, places window
            WINDOW_TITLE,  # Title & window name
            ui.DockPreference.DISABLED,  # Dock
            icon,  # Window icon
            500,  # Width
            300,  # Height
            True,  # Resizable
            enable_option,  # If has option button
            enable_help,  # If has help button
            True,  # If has close button
            padding_x=15,
            padding_y=15,
        )
        # self._window.flags = ui.WINDOW_FLAGS_FORCE_VERTICAL_SCROLLBAR
        self._window.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)  # if stage, dock near it

    def _callback(self) -> None:
        print("Button clicked to convert GeoJSON files")
        stage_url = self._usd_context.get_stage_url()
        geojson_folder_path = self._geojson_folder_path.model.get_value_as_string()
        _recursive = self._IsRecursive_CheckBox.model.get_value_as_bool()
        if geojson_folder_path != "":
            if os.path.exists(geojson_folder_path):
                geojson_folder_path = os.path.abspath(geojson_folder_path)
                print("Folder path to GeoJSON file(s) is: " + geojson_folder_path)
                if os.access(geojson_folder_path, os.R_OK):
                    if (
                        self._geojson_helper.convert_geojson_python(
                            stage_url=str(stage_url), download_url=str(geojson_folder_path), recursive=bool(_recursive)
                        )
                        != 0
                    ):
                        print("GeoJSON Conversion failed.")
                else:
                    print("User does not have read permissions for this folder.")
            else:
                print("Folder path to GeoJSON file(s) does not exist.")
        else:
            print("Folder path to GeoJSON file(s) is empty.")

    # def _check_ui_types(self) -> None:
    # print(type(self._lat))            # <class 'omni.ui._ui.FloatField'>
    # print(type(self._lat.model))      # <class 'omni.ui._ui.SimpleFloatModel'>
    # print(type(self._wms_User_Url))         # <class 'omni.ui._ui.StringField'>
    # print(type(self._wms_User_Url.model))   # <class 'omni.ui._ui.SimpleStringModel'>
    # print(type(self._cbWms))          # <class 'omni.ui._ui.ComboBox'>
    # print(type(self._cbWms.model))    # <class 'omni.ui._ui.AbstractItemModel'>

    def _default_function_string(
        self, string_field: omni.ui._ui.StringField, default_value: str, rectangle: omni.ui._ui.Rectangle
    ):
        if string_field.model.get_value_as_string() != default_value:
            string_field.model.set_value(default_value)
            rectangle.visible = False
        else:
            rectangle.visible = True

    def _float_field_changed(
        self, float_field: omni.ui._ui.FloatField, default_value: float, rectangle: omni.ui._ui.Rectangle
    ):
        if float_field.model.get_value_as_float() != default_value:
            rectangle.visible = True
        else:
            rectangle.visible = False

    def _string_field_changed(
        self, string_field: omni.ui._ui.StringField, default_value: float, rectangle: omni.ui._ui.Rectangle
    ):
        if string_field.model.get_value_as_string() != default_value:
            rectangle.visible = True
        else:
            rectangle.visible = False

    def _reset_button(self, model: omni.ui._ui.AbstractItemModel, default_value, rectangle: omni.ui._ui.Rectangle):
        model.set_value(default_value)
        rectangle.visible = False

    # TODO: how to set current index of a ComboBox?
    # def _set_default_combo_box(self, float_field : omni.ui._ui.ComboBox) -> None:
    #     float_field.model.set_value(default_value)

    def _get_window_flags(self):
        """
        Override windows flags to show proper title bar
        """
        return ui.WINDOW_FLAGS_NONE

    def _build_content(self) -> None:
        # print(dir(omni.ui._ui.Rectangle))
        # print(dir(omni.ui._ui.FloatField.model))
        # print(dir(ui.color))
        self.CollapsableFrame_style = {
            "CollapsableFrame": {
                "background_color": 0xFF343432,
                "secondary_color": 0xFF343432,
                "color": 0xFFAAAAAA,
                "border_radius": 4.0,
                "border_color": 0x0,
                "border_width": 0,
                "font_size": 14,
                "padding": 5,
            },
            "HStack::header": {"margin": 5},
            "CollapsableFrame:hovered": {"secondary_color": 0xFF3A3A3A},
            "CollapsableFrame:pressed": {"secondary_color": 0xFF343432},
        }
        self.icon_style = {
            "RadioButton": {"background_color": ui.color.transparent},
            "RadioButton:checked": {"background_color": ui.color.transparent},
            "RadioButton.Image": {"image_url": "${kit}/resources/icons/Close.png"},
            "RadioButton.Image:checked": {"image_url": "${kit}/resources/icons/FocalLength_Sample_24.png"},
        }
        self._web_map_service_radio_collection = ui.RadioCollection()
        self._web_coverage_service_radio_collection = ui.RadioCollection()
        with self._window.frame:
            with ui.ScrollingFrame(
                width=ui.Percent(100),
                height=ui.Percent(100),
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
            ):
                with ui.VStack(height=0):
                    with ui.CollapsableFrame(title="Settings", style=self.CollapsableFrame_style):
                        # with ui.VStack(spacing=10, alignment=ui.Alignment.RIGHT_CENTER, height=ui.Fraction(1)):
                        with ui.VStack(height=0):
                            #  Horizontal Stack
                            ui.Spacer(width=ui.Pixel(5))
                            with ui.HStack(alignment=ui.Alignment.CENTER):
                                ui.Spacer(width=ui.Pixel(10))
                                # Image Download URL Horizontal Stack
                                with ui.HStack(width=ui.Pixel(100), alignment=ui.Alignment.CENTER):
                                    ui.Label("File location(s): ", height=20, tooltip="TODO")
                                # Image Download URL field
                                with ui.HStack(alignment=ui.Alignment.CENTER):
                                    self._geojson_folder_path = ui.StringField(height=20)
                                    self._geojson_folder_path.model.set_value("./")
                                    ui.Spacer(width=ui.Pixel(5))
                                    with ui.HStack(width=20, height=20, alignment=ui.Alignment.CENTER):
                                        with ui.ZStack(alignment=ui.Alignment.CENTER):
                                            with ui.HStack(alignment=ui.Alignment.CENTER):
                                                ui.Spacer(width=ui.Pixel(7.5))
                                                with ui.VStack(width=0, alignment=ui.Alignment.CENTER):
                                                    ui.Spacer(height=ui.Pixel(8))
                                                    ui.Rectangle(
                                                        style={
                                                            "background_color": ui.color(81, 81, 81),
                                                            "border_radius": 5.0,
                                                        },
                                                        width=ui.Pixel(5),
                                                        height=ui.Pixel(5),
                                                        name="reset_invalid",
                                                        alignment=ui.Alignment.CENTER,
                                                    )
                                                    ui.Spacer(height=ui.Pixel(8))
                                                ui.Spacer(width=ui.Pixel(7.5))
                                            with ui.HStack(alignment=ui.Alignment.CENTER):
                                                # ui.Spacer(width=ui.Pixel(0))
                                                with ui.VStack(width=0, alignment=ui.Alignment.CENTER):
                                                    ui.Spacer(height=ui.Pixel(2))
                                                    self._geojson_folder_path_default = ui.Rectangle(
                                                        style={
                                                            "background_color": ui.color(80, 124, 153),
                                                            "border_radius": 5.0,
                                                        },
                                                        width=18,
                                                        height=18,
                                                        name="reset",
                                                        tooltip="Click to reset value",
                                                    )
                                                    ui.Spacer(height=ui.Pixel(2))
                                                # ui.Spacer(width=ui.Pixel(0))
                                            self._geojson_folder_path_default.visible = False
                                        self._geojson_folder_path_default.set_mouse_pressed_fn(
                                            lambda x, y, m, w: self._reset_button(
                                                self._geojson_folder_path.model, "./", self._geojson_folder_path_default
                                            )
                                        )
                                        self._geojson_folder_path.model.add_end_edit_fn(
                                            lambda x: self._string_field_changed(
                                                self._geojson_folder_path, "./", self._geojson_folder_path_default
                                            )
                                        )
                                ui.Spacer(width=ui.Pixel(10))
                            ui.Spacer(height=ui.Pixel(5))
                            with ui.HStack(width=ui.Percent(10), alignment=ui.Alignment.CENTER):
                                ui.Spacer(width=ui.Pixel(10))
                                # IsRecursive CheckBox and Label Horizontal Stack
                                with ui.HStack(alignment=ui.Alignment.LEFT_CENTER):
                                    self._IsRecursive_CheckBox = ui.CheckBox(alignment=ui.Alignment.CENTER)
                                    ui.Spacer(width=ui.Pixel(8))
                                    ui.Label(
                                        "Recursively check for GeoJSON files?",
                                        height=20,
                                        tooltip="Recursively check for GeoJSON files given the passed file directory?",
                                    )
                                ui.Spacer(width=ui.Pixel(10))
                            ui.Spacer(height=ui.Pixel(5))
                            # Convert GeoJSON File(s) button Horizontal Stack
                            with ui.HStack(alignment=ui.Alignment.CENTER):  # 3 nested HStack below
                                with ui.HStack(alignment=ui.Alignment.V_CENTER):  # Load button
                                    ui.Spacer(width=ui.Percent(5))
                                    self._load_button = ui.Button(
                                        "Convert GeoJSON File(s)",
                                        clicked_fn=lambda: self._callback(),  # button calls above _callback function
                                        tooltip="TODO",
                                        height=ui.Pixel(25),
                                        style={"border_radius": 5},
                                    )
                                    ui.Spacer(width=ui.Percent(5))
