# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui

from .button import InvisibleButton
from .constant import COLORS, DarkColors, LightColors
from .delegate import LabelDelegate
from .style import DefaultWidgetStyle, get_ui_style
from .utils import merge_dicts
from .window import PopupWindow


class CustomMenuItem:
    LIGHT_STYLE = {
        "Rectangle::custom_menuitem": {"background_color": COLORS.WIDGET_BACKGROUND_LIGHT, "border_radius": 0},
        "Rectangle::custom_menuitem:hovered": {"background_color": COLORS.CLR_4},
        "Rectangle::custom_menuitem:selected": {"background_color": COLORS.CLR_4},
    }
    DARK_STYLE = {
        "Rectangle::custom_menuitem": {"background_color": COLORS.WIDGET_BACKGROUND_DARK},
        "Rectangle::custom_menuitem:hovered": {"background_color": COLORS.CLR_4},
        "Rectangle::custom_menuitem:selected": {"background_color": COLORS.CLR_4},
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(self, value, create_widget_fn: callable, width, height, on_clicked_fn=None, selected=False):
        self._value = value
        self._on_clicked_fn = on_clicked_fn

        style = CustomMenuItem.UI_STYLES[get_ui_style()]

        widget_width = width - 8
        widget_height = height - 6
        with ui.ZStack(style=style):
            self._background_rectangle = ui.Rectangle(
                width=width,
                height=height,
                name="custom_menuitem",
                mouse_pressed_fn=(lambda x, y, key, m: self._on_mouse_pressed(key)),
            )
            with ui.Placer(offset_x=4, offset_y=3):
                self._widget = create_widget_fn(value, widget_width, widget_height)

        self._background_rectangle.selected = selected
        self._widget.selected = selected

    def _on_mouse_pressed(self, key):
        if self._on_clicked_fn is not None:
            self._on_clicked_fn(self._value)

    @property
    def selected(self):
        return self._background_rectangle.selected

    @selected.setter
    def selected(self, value):
        self._background_rectangle.selected = value


class CustomMenu(PopupWindow):
    LIGHT_STYLE = {"Window": {"background_color": COLORS.WIDGET_BACKGROUND_LIGHT}}
    DARK_STYLE = {"Window": {"background_color": COLORS.WIDGET_BACKGROUND_DARK}}
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self,
        values,
        create_widget_fns,
        menuitem_width,
        menuitem_height,
        selection=None,
        on_selection_changed_fn: callable = None,
        *args,
        **kwargs,
    ):
        self._on_selection_changed_fn = on_selection_changed_fn
        self._menu_items = []
        self._values = values
        self._selection = selection

        window_flags = ui.WINDOW_FLAGS_NO_RESIZE
        window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        window_flags |= ui.WINDOW_FLAGS_NO_CLOSE
        window_flags |= ui.WINDOW_FLAGS_NO_TITLE_BAR
        window_flags |= ui.WINDOW_FLAGS_NO_MOVE
        super().__init__(
            "CustomMenu",
            width=0,
            height=0,
            flags=window_flags,
            visible=False,
            dpi=ui.Workspace.get_dpi_scale(),
            *args,
            **kwargs,
        )

        with self.frame:
            with ui.VStack():
                for i in range(len(values)):
                    selected = True if selection is not None and i == selection else False
                    create_widget_fn = create_widget_fns[i] if i < len(create_widget_fns) else create_widget_fns[-1]
                    self._menu_items.append(
                        CustomMenuItem(
                            values[i],
                            create_widget_fn,
                            menuitem_width,
                            menuitem_height,
                            on_clicked_fn=self._on_clicked,
                            selected=selected,
                        )
                    )

        ui_style = get_ui_style()
        style = DefaultWidgetStyle.get_style(ui_style)
        style = merge_dicts(style, CustomMenu.UI_STYLES[ui_style])
        self.frame.set_style(style)

    def _on_clicked(self, value):
        self.selection = self._values.index(value)
        if self._on_selection_changed_fn is not None:
            self._on_selection_changed_fn(value)

        self.visible = False

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        if self._selection is not None and self._selection >= 0:
            self._menu_items[self._selection].selected = False
        self._selection = value
        self._menu_items[value].selected = True

    def show_at(self, widget, alignment=ui.Alignment.RIGHT, visible=True):
        if visible:
            if len(self._menu_items) == 0:
                return

            # show menu window
            self.visible = True
            if alignment == ui.Alignment.RIGHT:
                x = widget.screen_position_x + widget.computed_width
                y = widget.screen_position_y
            elif alignment == ui.Alignment.BOTTOM:
                x = widget.screen_position_x
                y = widget.screen_position_y + widget.computed_height
            else:
                # FIXME: Not sure if this widget is dis-allowing other alignment types...
                # use "background" widget's position for all other alignment types for now,
                # othewise x, y won't be defined before we get to the next section (adding offsets)
                x, y = widget.screen_position_x, widget.screen_position_y
            self.setPosition((int)(x), int(y))

            # adjust menu item width to fit window
            """
            width = self.width
            if width == 0:
                width = self.frame.width
            for item in self._menu_items:
                item.set_width(width)
            """
        else:
            self.visible = False

    def _on_triggered(self, index):
        self._on_selected_fn(index)


class CustomWidgetMenuItem:
    LIGHT_STYLE = {
        "MenuItem": {"background_color": LightColors.Background, "border_radius": 0, "color": LightColors.Text},
        "MenuItem:hovered": {"background_color": LightColors.BackgroundHovered},
        "MenuItem:selected": {"background_color": LightColors.BackgroundSelected},
    }
    DARK_STYLE = {
        "MenuItem": {"background_color": DarkColors.Background},
        "MenuItem:hovered": {"background_color": DarkColors.BackgroundHovered},
        "MenuItem:selected": {"background_color": DarkColors.BackgroundSelected},
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self, value, padding_x=4, padding_y=0, clicked_fn=None, on_value_changed_fn=None, selected=False, **kwargs
    ):
        self._clicked_fn = clicked_fn

        style = kwargs.get("style", self.UI_STYLES[get_ui_style()])

        self._delegate = kwargs.get("delegate", None)
        if self._delegate is None:
            self._delegate = LabelDelegate()

        with ui.ZStack(style=style):
            self._background_rectangle = ui.Rectangle(style_type_name_override="MenuItem", **kwargs)

            with ui.HStack(**kwargs):
                ui.Spacer(width=padding_x)
                with ui.VStack(**kwargs):
                    ui.Spacer(height=padding_y)
                    kwargs.pop("width", None)
                    kwargs.pop("height", None)
                    self._delegate.create_widget(value, style_type_name_override="MenuItem", **kwargs)
                    ui.Spacer(height=padding_y)
                ui.Spacer(width=padding_x)

            InvisibleButton(clicked_fn=self._on_click)

        self._background_rectangle.selected = selected

    def _on_click(self):
        if self._clicked_fn is not None:
            self._clicked_fn(self)

    @property
    def selected(self):
        return self._background_rectangle.selected

    @selected.setter
    def selected(self, value):
        self._background_rectangle.selected = value

    @property
    def value(self):
        return self._delegate.get_value()

    @value.setter
    def value(self, _value):
        self._delegate.set_value(_value)


class CustomWidgetMenu(PopupWindow):
    LIGHT_STYLE = {"Window": {"background_color": LightColors.Background}}
    DARK_STYLE = {"Window": {"background_color": DarkColors.Background}}
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self, values, delegate=None, selection=None, on_selection_changed_fn: callable = None, *args, **kwargs
    ):
        self._on_selection_changed_fn = on_selection_changed_fn
        self._values = values
        self._selection = selection

        window_flags = ui.WINDOW_FLAGS_NO_RESIZE
        window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        window_flags |= ui.WINDOW_FLAGS_NO_CLOSE
        window_flags |= ui.WINDOW_FLAGS_NO_TITLE_BAR
        window_flags |= ui.WINDOW_FLAGS_NO_MOVE
        width = kwargs.pop("width", 0)
        height = kwargs.pop("height", 0)
        window_kwargs = kwargs.copy()
        window_kwargs.pop("padding_x", 0)
        window_kwargs.pop("padding_y", 0)
        super().__init__(
            "##CustomWidgetMenu_" + str(hash(self)),
            width=width,
            height=height,
            flags=window_flags,
            visible=False,
            dpi=ui.Workspace.get_dpi_scale(),
            popup=True,
            padding_x=0,
            *args,
            **window_kwargs,
        )
        self._delegates = delegate
        self._menu_items = []

        ui_style = get_ui_style()
        style = DefaultWidgetStyle.get_style(ui_style)
        window_style = window_kwargs.get("style", self.UI_STYLES[ui_style])
        style = merge_dicts(style, window_style)
        self.frame.set_style(style)

        with self.frame:
            with ui.VStack():
                if len(values) == 0:
                    self._build_blank()
                else:
                    for i in range(len(values)):
                        selected = True if selection is not None and i == selection else False
                        if self._delegates is not None:
                            if type(self._delegates) == list:
                                delegate = self._delegates[i]
                            else:
                                delegate = self._delegates
                        else:
                            delegate = None
                        self._menu_items.append(
                            CustomWidgetMenuItem(
                                values[i], clicked_fn=self._on_clicked, selected=selected, delegate=delegate, **kwargs
                            )
                        )

    def _on_clicked(self, menuitem):
        self.selection = self._menu_items.index(menuitem)
        if self._on_selection_changed_fn is not None:
            self._on_selection_changed_fn(self._selection)

        self.visible = False

    def _build_blank(self):
        pass

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        if self._selection is None:
            # Do not support selection
            return
        if self._selection >= 0:
            self._menu_items[self._selection].selected = False
        self._selection = value
        if value >= 0:
            self._menu_items[value].selected = True

    def show_at(self, widget, alignment=ui.Alignment.RIGHT, visible=True, offset_x=0, offset_y=0):
        if visible:
            # show menu window
            self.visible = True
            if alignment == ui.Alignment.RIGHT:
                x = widget.screen_position_x + widget.computed_width
                y = widget.screen_position_y
            elif alignment == ui.Alignment.BOTTOM:
                x = widget.screen_position_x
                y = widget.screen_position_y + widget.computed_height
            elif alignment == ui.Alignment.RIGHT_BOTTOM:
                x = widget.screen_position_x + widget.computed_width
                y = widget.screen_position_y + widget.computed_height
            else:
                # FIXME: Not sure if this widget is dis-allowing other alignment types...
                # use "background" widget's position for all other alignment types for now,
                # othewise x, y won't be defined before we get to the next section (adding offsets)
                x, y = widget.screen_position_x, widget.screen_position_y
            x += offset_x
            y += offset_y
            self.setPosition(x - 0.5, y)
        else:
            self.visible = False

    def _on_triggered(self, index):
        self.selection = index
        self._on_selected_fn(index)


class CustomComboBoxDroplist(CustomWidgetMenu):
    def _build_blank(self):
        ui.Rectangle(height=24, style_type_name_override="ComboBox")
