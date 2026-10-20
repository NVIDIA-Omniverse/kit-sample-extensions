import asyncio
import typing

import omni.ui as ui
from omni.kit.window.preferences import PreferenceBuilder, register_page, unregister_page

from .time_settings import TIME_DISPLAY_SETTING, TIME_SETTINGS_TITLE, TimeDisplay, build_time_preferences

_page_instance = None
_TITLE = "Animation"


class AnimationPreferences(PreferenceBuilder):
    _frame_delegates: typing.Dict[str, typing.Callable[[PreferenceBuilder], None]] = {}

    def __init__(self):
        super().__init__(_TITLE)
        self._root_frame: typing.Optional[ui.Frame] = None

    @property
    def frame(self) -> typing.Optional[ui.Frame]:
        return self._root_frame

    @staticmethod
    def register_preferences_frame(title: str, build_fn: typing.Callable[[PreferenceBuilder], None]):
        """Register a frame build function."""
        AnimationPreferences._frame_delegates[title] = build_fn
        AnimationPreferences._dirty()

    @staticmethod
    def unregister_preferences_frame(title: str):
        """Un-Register a frame build function."""
        if title in AnimationPreferences._frame_delegates:
            del AnimationPreferences._frame_delegates[title]
            AnimationPreferences._dirty()

    @staticmethod
    def _dirty():
        _instance = get_instance()
        if _instance:
            _instance.rebuild()

    def rebuild(self):
        if self._root_frame:
            self._root_frame.rebuild()

    def build(self):
        self._root_frame = ui.Frame(build_fn=self._build)

    def _build(self):
        with ui.VStack(height=0, spacing=4):
            for title, build_fn in self._frame_delegates.items():
                with self.add_frame(title):
                    build_fn(self)

    @staticmethod
    def register_preferences():
        global _page_instance
        if _page_instance:
            return
        _page_instance = register_page(AnimationPreferences())

    @staticmethod
    def unregister_preferences():
        global _page_instance
        if _page_instance:
            unregister_page(_page_instance)
            _page_instance = None


def get_instance() -> AnimationPreferences:
    global _page_instance
    return _page_instance
