from pathlib import Path
from typing import Callable

import carb.dictionary
import carb.settings
import carb.tokens
from omni.kit.window.title import get_main_window_title

kWINDOW_UISTYLE_PATH = "/persistent/app/window/uiStyle"


def get_rgb_color(r: int, g: int, b: int):
    return (r << 16) | (g << 8) | b


class SettingBase:
    def __init__(self, path: str, modifier):
        self._path = path
        self._modifier = modifier
        settings = carb.settings.get_settings()
        self._sub = settings.subscribe_to_node_change_events(self._path, self._on_setting_event)
        self._on_value_changed()

    def __del__(self):
        self.destroy()

    def destroy(self):
        settings = carb.settings.get_settings()
        if self._sub:
            settings.unsubscribe_to_change_events(self._sub)
            self._sub = None
        self._modifier = None

    def _on_setting_event(self, item: carb.dictionary.Item, event_type: carb.settings.ChangeEventType):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self._on_value_changed()

    def _on_value_changed(self):
        pass


class SettingBool(SettingBase):
    def __init__(self, path: str, set_fn: Callable):
        self._set_fn = set_fn
        super().__init__(path, None)

    def _on_value_changed(self):
        settings = carb.settings.get_settings()
        value = settings.get_as_bool(self._path)
        self._set_fn(value)


class SettingSeparator(SettingBase):
    def __init__(self, path: str, modifier):
        settings = carb.settings.get_settings()
        settings.set_default((path + "/color"), 0x0076B9A0)
        settings.set_default(path + "/width", 2)
        super().__init__(path, modifier)

    def _on_value_changed(self):
        settings = carb.settings.get_settings()
        width = settings.get_as_int(self._path + "/width")
        color = settings.get_as_int(self._path + "/color")
        self._modifier.setSeparator(color, width)


class SettingBorder(SettingBase):
    def __init__(self, path: str, modifier):
        settings = carb.settings.get_settings()
        settings.set_default((path + "/color"), 0x00A0A0A0)
        settings.set_default(path + "/width", 3)
        super().__init__(path, modifier)

    def _on_value_changed(self):
        settings = carb.settings.get_settings()
        width = settings.get_as_int(self._path + "/width")
        color = settings.get_as_int(self._path + "/color")
        self._modifier.setBorderWidth(width)
        self._modifier.setColor("border", color)


class SettingColor(SettingBase):
    def __init__(self, path: str, modifier):
        settings = carb.settings.get_settings()
        settings.set_default(kWINDOW_UISTYLE_PATH, "NvidiaDark")
        ui_style = settings.get_as_string(kWINDOW_UISTYLE_PATH)
        if ui_style == "NvidiaDark":
            settings.set_default((path + "/caption"), get_rgb_color(69, 69, 69))
            settings.set_default((path + "/client"), get_rgb_color(36, 36, 31))
            settings.set_default((path + "/button"), get_rgb_color(204, 204, 204))
            settings.set_default((path + "/minmax"), get_rgb_color(99, 99, 99))
            settings.set_default((path + "/close"), get_rgb_color(232, 17, 35))
            settings.set_default((path + "/minmax_clicked"), get_rgb_color(119, 119, 119))
            settings.set_default((path + "/close_clicked"), get_rgb_color(232, 47, 65))
        else:
            settings.set_default((path + "/caption"), get_rgb_color(224, 224, 224))
            settings.set_default((path + "/client"), get_rgb_color(224, 224, 224))
            settings.set_default((path + "/button"), get_rgb_color(56, 56, 56))
            settings.set_default((path + "/minmax"), get_rgb_color(188, 188, 188))
            settings.set_default((path + "/close"), get_rgb_color(232, 17, 35))
            settings.set_default((path + "/minmax_clicked"), get_rgb_color(158, 158, 158))
            settings.set_default((path + "/close_clicked"), get_rgb_color(232, 47, 65))

        super().__init__(path, modifier)

    def _on_value_changed(self):
        settings = carb.settings.get_settings()
        names = [
            ("caption", "caption"),
            ("client", "client"),
            ("minmax", "min"),
            ("minmax", "max"),
            ("close", "close"),
            ("minmax_clicked", "min_clicked"),
            ("minmax_clicked", "max_clicked"),
            ("close_clicked", "close_clicked"),
            ("button", "button"),
        ]

        for src, dst in names:
            path = self._path + "/" + src
            color = settings.get_as_int(path)
            if self._modifier:
                self._modifier.setColor(dst, color)


class SettingTitleFormat(SettingBase):
    def __init__(self, path: str, modifier):
        self._field_subs = []
        settings = carb.settings.get_settings()
        settings.set_default(path, "Omniverse View")
        super().__init__(path, modifier)

    def destroy(self):
        self._clean_subs()
        super().destroy()

    def _clean_subs(self):
        settings = carb.settings.get_settings()
        for sub_id in self._field_subs:
            settings.unsubscribe_to_change_events(sub_id)
        self._field_subs.clear()

    def _on_value_changed(self):
        settings = carb.settings.get_settings()
        title = settings.get_as_string(self._path).strip()
        self._modifier.delAllRegions()

        title = carb.tokens.get_tokens_interface().resolve(title)

        reg_count = 0
        current = 0
        length = len(title)
        while current < length:
            start = title.find("{", current)
            if start == -1:
                # No more regiion, trade all as a text region
                text = title[current:]
                self._modifier.addRegion(f"R{reg_count}", "text", text, None)
                reg_count += 1
                break

            if start > current:
                # New regiion followed, keep current as a text region
                text = title[current:start]
                # No strip() here, keep the blanks
                self._modifier.addRegion(f"R{reg_count}", "text", text, None)
                reg_count += 1

            end = title.find("}", start + 1)
            reg_text = None
            if end == -1:
                carb.log_warn(f"Bad title string, unmatched bracket: {title}")
                reg_text = title[start + 1 :]
                reg_text = reg_text.strip()
                current = length
            else:
                reg_text = title[start + 1 : end]
                reg_text = reg_text.strip()
                current = end + 1

            attributes = None
            pos = reg_text.find(",")
            if pos != -1:
                attributes = reg_text[pos + 1 :]
                reg_text = reg_text[:pos]
                attributes = attributes.strip()
                reg_text = reg_text.strip()

            type_name = "text"
            context = reg_text
            pos = reg_text.find(":")
            if pos != -1:
                type_name = reg_text[:pos].lower().strip()
                context = reg_text[pos + 1 :]
                context = context.strip()
            else:
                type_name = reg_text.lower().strip()
                context = None

            if type_name == "image":
                file_path = Path(context)
                context = file_path.absolute().as_posix()
            elif type_name == "verkey":
                type_name = "text"
                sub_id = settings.subscribe_to_node_change_events(context, self._on_setting_event)
                context = settings.get_as_string(context)
                pos = context.find("+")
                if pos != -1:
                    context = context[:pos]
                else:
                    is_external_bbuild = settings.get_as_bool("/privacy/externalBuild")
                    if is_external_bbuild:
                        pos = pos = context.find("-")
                        if pos != -1:
                            context = context[:pos]

                self._field_subs.append(sub_id)
            elif type_name == "file":
                # Get current file name (stage)
                title_ext = get_main_window_title()
                if title_ext:
                    context = title_ext.get_full_title()

            if context is None:
                context = ""

            self._modifier.addRegion(f"R{reg_count}", type_name, context, attributes)
            reg_count += 1
