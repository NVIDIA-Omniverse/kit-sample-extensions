import os
from collections.abc import Callable

import carb
import omni.kit.ui
import omni.ui as ui
from omni.kit.property.usd.usd_property_widget_builder import UsdPropertiesWidgetBuilder
from omni.kit.window.filepicker import FilePickerDialog

from . import style as sty
from . import ui_const as uic
from .utils import *

# Disable the Collision UI
# SpawnEventTypes = ["Key Pressed", "Simulation Start", "Collision"]
SpawnEventTypes = ["Key Pressed", "Simulation Start"]


def build_xyz(label="Foo"):
    def build_scalar(axis):
        # axis should be either X, Y, or Z
        colors = {"X": 0xFF5555AA, "Y": 0xFF76A371, "Z": 0xFFA07D4F}
        with ui.ZStack():
            with ui.HStack():
                range_min, range_max = -100.0, 100.0
                widget_kwargs = {"model": None, "step": 1}
                if range_min < range_max:
                    widget_kwargs["min"] = range_min
                    widget_kwargs["max"] = range_max
                UsdPropertiesWidgetBuilder._create_drag_or_slider(ui.FloatDrag, ui.FloatSlider, **widget_kwargs)
                # UsdPropertiesWidgetBuilder._create_control_state(None, no_control_state=True)
            with ui.HStack():
                with ui.ZStack(width=14):
                    ui.Rectangle(
                        name="vector_label",
                        style={
                            "background_color": colors[axis],
                            "border_radius": 3,
                            "corner_flag": ui.CornerFlag.LEFT,
                        },
                    )
                    ui.Label(axis, name="vector_label", alignment=ui.Alignment.CENTER)

    with ui.HStack():
        with ui.HStack(width=40):
            with ui.ZStack():
                label_tooltip = "\nRight click it to disable or delete it. "
                # This rectangle is act as a hover hint helper
                ui.Rectangle(
                    style={":hovered": {"background_color": 0xFF444444}, "background_color": 0xFF333333},
                )
                ui.Label(label, name="title", tooltip=label_tooltip)
            ui.Spacer(width=2)
        with ui.HStack():
            build_scalar("X")
            ui.Spacer(width=2)
            build_scalar("Y")
            ui.Spacer(width=2)
            build_scalar("Z")


def open_file_diag():
    file_diag_window = FilePickerDialog("Foobar File Picker")


def build_open_folder_btn():
    text = omni.kit.ui.get_custom_glyph_code("${glyphs}/Open_Folder.svg")
    ui.Label(text, mouse_pressed_fn=lambda x, y, b, a: open_file_diag())


def make_it_accept_drop(widget: ui.StringField):
    def accept_all_drop_fn(url):
        # A simple accept_drop_fn that accepts everything
        return True

    def drop_fn(event, widget: ui.StringField):
        widget.model.set_value(str(event.mime_data))

    widget.set_accept_drop_fn(accept_all_drop_fn)
    widget.set_drop_fn(lambda a, w=widget: drop_fn(a, w))


class ComboBoxItem(ui.AbstractItem):
    def __init__(self, text):
        super().__init__()
        self.model = ui.SimpleStringModel(text)


class ComboBoxModel(ui.AbstractItemModel):
    def __init__(self, combo_strings):
        super().__init__()
        self._current_index = ui.SimpleIntModel()
        self._current_index.add_value_changed_fn(lambda a: self._item_changed(None))
        self._items = [ComboBoxItem(text) for text in combo_strings]

    def get_item_children(self, item=None):
        return self._items

    def get_item_value_model(self, item=None, column_id=0):
        if item is None:
            return self._current_index
        return item.model

    def get_selected_item_value_model(self):
        selectedIndex = self.get_item_value_model().as_int
        selectedItem = self.get_item_children()[selectedIndex]
        return self.get_item_value_model(selectedItem)

    def set_selected_item(self, item_value):
        item_strings = [item.model.as_string for item in self._items]
        if item_value in item_strings:
            self._current_index.set_value(int(item_strings.index(item_value)))

    def set_selected_index(self, index):
        self._current_index.set_value(index)


class SpawnEntityWizardWindow(ui.Window):
    def __init__(self, name, icon_path):
        self._name = name
        super().__init__(name, height=600, width=500, raster_policy=ui.RasterPolicy.NEVER)
        self.visible = False
        self._spawn_graph_name_model = ui.SimpleStringModel("MySpawnGraph")
        self._source_path_model = []
        self._spawn_event_model = {
            "EventType": "Key Pressed",
            "Key": "A",
            "Ctrl": False,
            "Shift": False,
            "Alt": False,
            "Consume": True,
        }  # e.g. {"Event": "Key Pressed", "Key":"A", "Ctrl":True, "Shift":False, "Alt":False}
        self._destroy_event_model = {
            "EventType": "Simulation Stop",
            "Key": "D",
            "Ctrl": False,
            "Shift": False,
            "Alt": False,
            "Consume": True,
        }
        self._entity_source_sub_frame = None
        self._spawn_event_sub_frame = None
        self._icon_path = icon_path
        self._spawn_event_combbox = None
        # Disable the Collision UI
        # self._collision_frame_needs_update = False
        self._frame_needs_rebuild = False

    def on_startup(self):
        with self.frame:
            scrollframe = ui.ScrollingFrame(height=ui.Fraction(1))
            with scrollframe:
                with ui.VStack(height=ui.Fraction(1), spacing=0, style=sty.w_vstack_plain):
                    self.build_frame()
                    self.build_buttons()

    def on_shutdown(self):
        self._spawn_graph_name_model = None
        self._source_path_model.clear()
        self._spawn_event_model.clear()
        self._destroy_event_model.clear()
        self._spawn_event_combbox = None
        self._entity_source_sub_frame = None
        self._spawn_event_sub_frame = None
        # Disable the Collision UI
        # self._collision_frame_needs_update = False
        super().destroy()

    def reset_models(self):
        self._spawn_graph_name_model.set_value("MySpawnGraph")
        self._source_path_model = []
        self._spawn_event_model = {
            "EventType": "Key Pressed",
            "Key": "A",
            "Ctrl": False,
            "Shift": False,
            "Alt": False,
            "Consume": True,
        }  # e.g. {"Event": "Key Pressed", "Key":"A", "Ctrl":True, "Shift":False, "Alt":False}
        self._destroy_event_model = {
            "EventType": "Simulation Stop",
            "Key": "D",
            "Ctrl": False,
            "Shift": False,
            "Alt": False,
            "Consume": True,
        }
        self._spawn_event_combbox = None
        self._frame_needs_rebuild = True

    def on_cancel(self):
        self.reset_models()
        self.visible = False

    def on_update(self, dt):
        if not self or not self.visible:
            return
        # Disable the Collision UI
        # if self._collision_frame_needs_update:
        #     self._collision_frame_needs_update = False
        #     self._build_spawn_event_collision()
        if self._frame_needs_rebuild:
            self.build_frame()
            self._frame_needs_rebuild = False

    def on_toggle(self):
        self.visible = not self.visible

    def build_frame(self):
        self._build_graph_name()
        self._build_entity_source_paths()
        self._build_spawn_events()

    def build_buttons(self):
        with ui.VStack(height=0):
            ui.Spacer(height=20, style=sty.w_vspacer_style)
            with ui.HStack(height=35, spacing=10, style=sty.w_main_buttons):
                ui.Spacer(width=10)
                ui.Button(
                    "Cancel",
                    width=60,
                    clicked_fn=self.on_cancel,
                    tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_CANCEL),
                )
                ui.Button(
                    "Reset",
                    width=60,
                    clicked_fn=self.reset_models,
                    tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_RESET_ALL),
                )
                ui.Spacer()
                ui.Button(
                    "Create Spawn Graph",
                    width=180,
                    clicked_fn=self._build_spawn_graph,
                    tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_CREATE_SPAWN_GRAPH),
                )
                ui.Spacer(width=10)
            ui.Spacer(height=20, style=sty.w_vspacer_style)

    def _build_graph_name(self):
        with ui.VStack(height=0):
            ui.Spacer(height=20, style=sty.w_vspacer_style)
            with ui.HStack():
                ui.Spacer(width=20)
                ui.Label("Graph Name", style=sty.w_section_title, width=0)
                ui.Spacer(width=20)
                ui.StringField(model=self._spawn_graph_name_model, height=16)
                ui.Spacer(width=20)
            ui.Spacer(height=20, style=sty.w_vspacer_style)
        ui.Separator(height=0, style=sty.w_section_separator)

    # delete buttons after each source path assets to delete it
    def _build_delete_btn(self, model):
        text = omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_delete.svg")

        def on_click():
            self._source_path_model.remove(model)
            self._build_entity_source_list_sub_frame()

        ui.Button(text, clicked_fn=on_click, tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_REMOVE_SOURCE))

    # utility function to make the area accept the drop
    def _make_source_paths_accept_drop(self, receiver_widget: ui.Widget, callback_fn=None):
        def accept_all_drop_fn(url):
            # A simple accept_drop_fn that accepts everything
            receiver_widget.style = sty.w_drop_area_highlight
            return True

        def drop_fn(event):
            self._source_path_model.append(ui.SimpleStringModel(str(event.mime_data)))
            if callback_fn:
                callback_fn()
            receiver_widget.style = sty.w_drop_area

        receiver_widget.set_accept_drop_fn(accept_all_drop_fn)
        receiver_widget.set_drop_fn(lambda a: drop_fn(a))

    # A sub-frame to list all the drag & dropped assets
    def _build_entity_source_list_sub_frame(self):
        if not self._entity_source_sub_frame:
            self._entity_source_sub_frame = ui.Frame()
        with self._entity_source_sub_frame:
            with ui.ZStack(height=ui.Fraction(1), width=ui.Fraction(1)):
                # spacer for minimum height
                ui.Spacer(height=ui.Pixel(40))
                list_scrolling_frame = ui.ScrollingFrame(
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                    height=ui.Fraction(1),
                    style={"padding": 4},
                )
                with list_scrolling_frame:
                    with ui.VStack(spacing=5):
                        for src_path_model in self._source_path_model:
                            with ui.HStack(height=20, spacing=5):
                                field = ui.StringField(src_path_model)
                                make_it_accept_drop(field)

                                with ui.VStack(width=0):
                                    style = {"color": 0xFF8E8E8E}
                                    style["image_url"] = str(os.path.join(self._icon_path, "find.svg"))
                                    ui.Button(
                                        style=style,
                                        width=28,
                                        height=28,
                                        tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_LOCATE_ASSET),
                                        clicked_fn=lambda model=src_path_model: locate_file(model),
                                    )

                                with ui.VStack(width=30):
                                    self._build_delete_btn(src_path_model)

                ui.Rectangle(height=ui.Fraction(1), width=ui.Fraction(1), style=sty.w_scrollingframe_border)

                no_sources_label = ui.Label(
                    "No Sources Added", alignment=ui.Alignment.CENTER, style=sty.w_scrollingframe_nosources
                )

                def scrolling_frame_content_update():
                    no_sources_label.visible = len(self._source_path_model) == 0

                list_scrolling_frame.set_build_fn(scrolling_frame_content_update)

    # A sub-frame as a drop area for source assets, e.g. files & stage prims
    def _build_entity_source_drop_sub_frame(self):
        drop_frame = ui.Frame()
        with drop_frame:
            drag_n_drop_area = ui.ZStack(
                height=50, style=sty.w_drop_area, tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_SOURCE_DROP)
            )
            self._make_source_paths_accept_drop(drag_n_drop_area, self._build_entity_source_list_sub_frame)
            with drag_n_drop_area:
                with ui.ZStack():
                    ui.Rectangle()
                    ui.Label("Drag and drop Assets or Stage Prims here", alignment=ui.Alignment.CENTER)

            def reset_drop_area(value):
                if not value:
                    drag_n_drop_area.style = sty.w_drop_area

            drag_n_drop_area.set_mouse_hovered_fn(reset_drop_area)

    def _clear_all_on_click(self):
        self._source_path_model.clear()
        self._build_entity_source_drop_sub_frame()
        self._build_entity_source_list_sub_frame()

    # Entry point to build the entity source frame
    def _build_entity_source_paths(self):
        with ui.VStack(height=ui.Fraction(1), spacing=0, style=sty.w_vstack_plain):
            ui.Spacer(height=20, style=sty.w_vspacer_style)
            with ui.HStack():
                ui.Spacer(width=20)
                with ui.VStack(height=ui.Fraction(1), spacing=10):
                    with ui.HStack(height=0):
                        ui.Label(
                            "Entity Sources",
                            style=sty.w_section_title,
                            height=0,
                            tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_SECTION_ENTITY_SOURCES),
                        )
                        ui.Button(
                            "Clear All",
                            width=10,
                            clicked_fn=self._clear_all_on_click,
                            style=sty.w_clear_button,
                            tooltip_fn=lambda: self._create_tooltip(uic.TT_WIZ_BUTTON_CLEAR_ALL_SOURCES),
                        )
                    self._build_entity_source_drop_sub_frame()
                    self._build_entity_source_list_sub_frame()
                ui.Spacer(width=20)
            ui.Spacer(height=20, style=sty.w_vspacer_style)
        ui.Separator(height=0, style=sty.w_section_separator)

    # Disable the Collision UI
    # # utility function to make the collision area accept the drop
    # def _make_collision_accept_drop(self, receiver_widget, callback_fn=None):
    #     def accept_all_drop_fn(url):
    #         receiver_widget.style = sty.w_drop_area_highlight
    #         # TODO: Check if it is a stage prim
    #         return "EventType" in self._spawn_event_model.keys() and self._get_selected_string(self._spawn_event_model["EventType"]) == "Collision"

    #     def drop_fn(event):
    #         if "Prim" in self._spawn_event_model.keys():
    #             self._spawn_event_model["Prim"].set_value(str(event.mime_data))
    #         else:
    #             self._spawn_event_model["Prim"] = ui.SimpleStringModel(str(event.mine_data))
    #         self._collision_frame_needs_update = True
    #     receiver_widget.set_accept_drop_fn(accept_all_drop_fn)
    #     receiver_widget.set_drop_fn(lambda a: drop_fn(a))
    #     receiver_widget.style = sty.w_drop_area

    # Store the Ctrl, Alt, Shift, Key, Consume values to the _spawn_event_model
    def _spawn_event_check_box(self, dict_event_type, dict_key, dict_key_value):
        self._spawn_event_model[dict_key] = dict_key_value

    # The spawn event can be "Key Pressed", "Simulation Start"
    # Some of them requires detail info and is present on the sub-frame
    def _build_spawn_event_detail_sub_frame(self):
        if not self._spawn_event_sub_frame:
            self._spawn_event_sub_frame = ui.Frame()
        self._spawn_event_sub_frame.clear()
        event_type_string = self._get_selected_string(self._spawn_event_model["EventType"])
        if event_type_string == "Key Pressed":
            with self._spawn_event_sub_frame:
                with ui.VStack(spacing=10, height=0):
                    with ui.HStack(spacing=10, height=0):
                        ui.Label("Key Binding", height=20, width=65)

                        ui.Spacer(height=0, width=30)

                        def _setup_checkbox_group(name):
                            with ui.VStack(height=20):
                                ui.Spacer(height=3)
                                model = ui.CheckBox(width=20, height=20).model
                            # model.add_value_changed_fn(lambda model, dict_event_type="Key Pressed", \
                            #     dict_key=name:self._spawn_event_check_box(dict_event_type,dict_key,model.as_bool))
                            # if name in self._spawn_event_model.keys():
                            #     model.set_value(self._spawn_event_model[name])
                            self._spawn_event_model[name] = model
                            ui.Label(name, height=20)

                        with ui.HStack(height=0, width=0):
                            _setup_checkbox_group("Ctrl")
                        ui.Spacer(width=10, height=0)
                        with ui.HStack(height=0, width=0):
                            _setup_checkbox_group("Shift")
                        ui.Spacer(width=10, height=0)
                        with ui.HStack(height=0, width=0):
                            _setup_checkbox_group("Alt")

                        ui.Spacer(height=0, width=10)

                        keyboard_key = ui.ComboBox(False, *ALLOWED_TOKEN_KEY_INPUTS, width=60)
                        self._spawn_event_model["Key"] = keyboard_key.model

                        ui.Line(style=sty.w_parameter_end_line, alignment=ui.Alignment.CENTER)

                        keybind_reset_button = self._build_reset_button(
                            uic.DEFAULT_KEY_INDEX,
                            keyboard_key.model,
                            self._reset_model_value,
                            [keyboard_key.model, uic.DEFAULT_KEY_INDEX],
                        )

                    # TODO: Consume hidden for now until functional
                    # with ui.HStack(spacing=12, width=0, visible=False):
                    #     ui.Label("Consume")
                    #     ui.Spacer()
                    #     with ui.HStack(spacing=10, width=0):
                    #         model=ui.CheckBox(width=20).model
                    #         model.set_value(True)
                    #         self._spawn_event_model["Consume"] = model
                    # model.add_value_changed_fn(lambda model, dict_event_type="Key Pressed", \
                    #     dict_key="Consume":self._spawn_event_check_box(dict_event_type,dict_key,model.as_bool))
                    # if "Consume" in self._spawn_event_model.keys():
                    #     model.set_value(self._spawn_event_model["Consume"])
                    # else:
                    #     model.set_value(True)
        # Disable the Collision UI
        # elif event_type_string == "Collision":
        #     self._build_spawn_event_collision()
        else:
            self._spawn_event_sub_frame.height = ui.Length(0)
            with self._spawn_event_sub_frame:
                # empty vstack to trigger resizing empty frame
                ui.VStack(height=0, style={"margin": 0, "padding": 0})

    # Disable the Collision UI
    # Build the delete button in the collision subframe to remove the selected prim
    # It will trigger the rebuild of the collision subframe
    # def _build_collision_delete_btn(self):
    #     text = omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_delete.svg")
    #     def on_click():
    #         self._spawn_event_model.pop("Prim")
    #         self._spawn_event_model.pop("Consume")
    #         self._collision_frame_needs_update = True
    #     ui.Button(text, clicked_fn=on_click, alignment=ui.Alignment.RIGHT)

    # # Build the collision sub-frame
    # def _build_spawn_event_collision(self):
    #     if "Prim" not in self._spawn_event_model.keys() or not self._spawn_event_model["Prim"]:
    #         with self._spawn_event_sub_frame:
    #             drag_n_drop_area = ui.ZStack(height=50, style=sty.w_drop_area)
    #             self._make_collision_accept_drop(drag_n_drop_area)
    #             with drag_n_drop_area:
    #                 ui.Rectangle()
    #                 ui.Label("Drag and drop a Stage Prims here", alignment=ui.Alignment.CENTER)

    #         def reset_drop_area(value):
    #             if not value:
    #                 drag_n_drop_area.style = sty.w_drop_area

    #         drag_n_drop_area.set_mouse_hovered_fn(reset_drop_area)
    #     else:
    #         with self._spawn_event_sub_frame:
    #             with ui.VStack(spacing=20, width=0):
    #                 with ui.HStack(spacing=10, width=ui.Percent(100), style={"Button":{"alignment":ui.Alignment.RIGHT}}):
    #                     ui.Label("Prim")
    #                     ui.Spacer(width=30)
    #                     collision_prim = ui.StringField(width=300, model=self._spawn_event_model["Prim"])
    #                     #collision_prim.model.set_value(self._spawn_event_model["Prim"])
    #                     collision_prim.enabled = False
    #                     #ui.Spacer(width=40)
    #                     self._build_collision_delete_btn()
    #                 with ui.HStack(spacing=12, width=0):
    #                     ui.Label("Consume")
    #                     ui.Spacer()
    #                     with ui.HStack(spacing=10, width=0):
    #                         model=ui.CheckBox(width=20).model
    #                         model.set_value(True)
    #                         self._spawn_event_model["Consume"] = model
    #                         # model.add_value_changed_fn(lambda model, dict_event_type="Collision", \
    #                         #     dict_key="Consume":self._spawn_event_check_box(dict_event_type,dict_key,model.as_bool))

    #                         # if "Consume" in self._spawn_event_model.keys():
    #                         #     model.set_value(self._spawn_event_model["Consume"])
    #                         # else:
    #                         #     model.set_value(True)

    # utility function for spawn event type selection combobox
    def _on_spawn_type_selection_changed(self, model, item):
        # selectedIndex = model.get_item_value_model().as_int
        # selectedItem = model.get_item_children()[selectedIndex]
        # selectedString = model.get_item_value_model(selectedItem).as_string
        # self._spawn_event_model.clear()
        self._spawn_event_model["EventType"] = model
        self._update_spawn_event_combobox_tooltip()
        self._build_spawn_event_detail_sub_frame()

    # Build the spawn event type selection combo box
    def _build_spawn_type_combbox(self, index):
        global SpawnEventTypes
        # self._spawn_event_combobox = ui.ComboBox(ComboBoxModel(["Key Pressed", "Simulation Start", "Collision"]), width=130)
        self._spawn_event_combobox = ui.ComboBox(ComboBoxModel(["Key Pressed", "Simulation Start"]), width=130)
        self._spawn_event_model["EventType"] = self._spawn_event_combobox.model

        # combobox = ui.ComboBox(index, "Key Pressed", "Simulation Start", "Collision", width=130)
        # self._spawn_event_model["EventType"] = combobox.model
        self._update_spawn_event_combobox_tooltip()
        self._spawn_event_model["EventType"].add_item_changed_fn(self._on_spawn_type_selection_changed)

    def _update_spawn_event_combobox_tooltip(self):
        self._spawn_event_combobox.set_tooltip_fn(
            lambda: self._create_tooltip(
                uic.TT_SPAWN_EVENT_TYPES[
                    self._spawn_event_combobox.model._items[
                        self._spawn_event_combobox.model._current_index.as_int
                    ].model.as_string
                ]
            )
        )

    # Entry point to build the Spawn Event section
    def _build_spawn_events(self):
        with ui.VStack(height=0):
            ui.Spacer(height=20, style=sty.w_vspacer_style)
            with ui.HStack(height=0):
                ui.Spacer(width=20)
                with ui.VStack(spacing=10):
                    ui.Label("Spawn Event", style=sty.w_section_title, height=0)
                    with ui.HStack(spacing=10, width=0, height=0):
                        ui.Label("Type", width=65)
                        ui.Spacer(width=30)
                        self._build_spawn_type_combbox(SpawnEventTypes.index(self._spawn_event_model["EventType"]))
                    self._build_spawn_event_detail_sub_frame()
                ui.Spacer(width=20)
            ui.Spacer(height=20, style=sty.w_vspacer_style)
        ui.Separator(height=0, style=sty.w_section_separator)

    # Get the selected string out of the ComboBox model
    def _get_selected_string(self, model):
        selectedIndex = model.get_item_value_model().as_int
        selectedItem = model.get_item_children()[selectedIndex]
        selectedString = model.get_item_value_model(selectedItem).as_string
        return selectedString

    def _build_spawn_graph(self):
        # if not self._source_path_model:
        #     carb.log_error("The Entity Sources is not correctly setup!")
        #     return
        if not self._spawn_event_model:
            carb.log_error("The Spawn Event is not correctly setup!")
            return  # TODO: MAKE a prompt here
        elif not self._spawn_graph_name_model.as_string:
            carb.log_error("The Graph Name is not correctly setup ")
            return  # TODO: MAKE a prompt here

        # with omni.kit.undo.group():
        spawner_graph = create_spawner_graph(self._spawn_graph_name_model.as_string)

        # Create spawn event node
        event_type = self._get_selected_string(self._spawn_event_model["EventType"])

        if event_type == "Key Pressed":
            event_index = 0
            index = self._spawn_event_model["Key"].get_item_value_model().as_int
            event_inputs = {
                "keyIn": ALLOWED_TOKEN_KEY_INPUTS[index],
                "ctrlIn": self._spawn_event_model["Ctrl"].as_bool,
                "shiftIn": self._spawn_event_model["Shift"].as_bool,
                "altIn": self._spawn_event_model["Alt"].as_bool,
            }
        elif event_type == "Simulation Start":
            event_index = 1
            event_inputs = {}

        spawn_event_attr = create_spawn_event_nodes(spawner_graph, event_index, event_inputs)

        # Create destroy event node

        # Create an identity transform matrix node
        transform_output, exec_ins = create_transform_nodes(spawner_graph)

        # Create the spawn entity node and connect to the spawn event node, source path node, transform matrix node
        spawn_entity_node, loop_exec_out = create_spawn_entity_node(
            spawn_event_attr, transform_output, spawner_graph=spawner_graph
        )

        # Connect random generator nodes
        for exec_in in exec_ins:
            og.Controller.connect(loop_exec_out, exec_in)

        # Create the destroy entity node connect from the spawn entity node
        destroy_entity_node = create_destroy_entity_node(
            spawn_entity_node=spawn_entity_node, spawner_graph=spawner_graph
        )

        # Set source paths in spawn entity node
        source_paths = []
        for model in self._source_path_model:
            source_paths.append(model.as_string)
        set_spawn_source_paths(spawn_entity_node, source_paths)

        self.visible = False
        self.reset_models()
        # self._build_entity_source_list_sub_frame()
        # self._build_spawn_events()

    def add_source_path(self, path: str):
        self._source_path_model.append(ui.SimpleStringModel(path))

    def _create_tooltip(self, text: str):
        with ui.ZStack(style=sty.tooltip):
            ui.Label(text, style=sty.tooltip_text)

    def _build_reset_button(
        self,
        default_value_to_compare,
        model: ui.AbstractValueModel,
        reset_fn: Callable,
        reset_fn_args=[],
    ) -> ui.Rectangle:
        btn = None
        height_value = 12
        with ui.VStack(width=0, style={"margin": 0}):
            ui.Spacer()
            with ui.ZStack(width=12, height=height_value):
                with ui.HStack(width=12, height=height_value):
                    ui.Spacer(width=3)
                    with ui.VStack(width=12, height=height_value):
                        ui.Spacer()
                        ui.Rectangle(width=5, height=5, name="reset_invalid", style=sty.button_reset_off)
                        ui.Spacer()
                btn = ui.Rectangle(
                    width=12,
                    height=12,
                    name="reset",
                    alignment=ui.Alignment.V_CENTER,
                    style=sty.button_reset_on,
                    tooltip_fn=lambda: self._create_tooltip(uic.TT_BUTTON_RESET),
                    margin=0,
                )
                btn.visible = False
            ui.Spacer()

        def reset():
            reset_fn(*reset_fn_args)
            btn.visible = False

        btn.set_mouse_pressed_fn(lambda x, y, z, w: reset())

        model.get_item_value_model().add_value_changed_fn(
            lambda value, _=None: self._update_reset_button(value, default_value_to_compare, btn)
        )

        return btn

    def _update_reset_button(self, value, default_value, btn):
        if type(value) is ui.AbstractItemModel:
            value = value.get_item_value_model()
        elif type(value) is ui.SimpleBoolModel:
            value = value.as_bool
        elif type(value) is ui.SimpleFloatModel:
            value = value.as_float
        elif type(value) is ui.SimpleIntModel:
            value = value.as_int

        btn.visible = value != default_value

    def _reset_model_value(self, model, value):
        if model is None or value is None:
            return

        model.get_item_value_model().set_value(value)
