from omni import ui
from omni.kit.widget.timeline import Scrubber, do_later


class CurveEditorScrubber(Scrubber):
    def __init__(self, timeline_view, frame):
        super().__init__(timeline_view, frame)

    def _get_is_listener(self):
        # return CurveEditorTimeline's _is_listener
        return self._timeline_view._is_listener

    def _get_is_presenter(self):
        if self._timeline_view._live_session == None:
            return False
        else:
            return self._timeline_view._live_session.am_i_presenter()

    def _on_mouse_pressed(self, x, y, button, modifier):
        if self._get_is_listener():
            return
        else:
            super()._on_mouse_pressed(x, y, button, modifier)

    def _on_mouse_moved(self, x, y, modifier, c):
        if self._get_is_listener():
            return
        else:
            super()._on_mouse_moved(x, y, modifier, c)

    def _on_mouse_released(self, x, y, button, modifier):
        if self._get_is_listener():
            return
        else:
            super()._on_mouse_moved(x, y, button, modifier)

    def _set_draggable(self, is_draggable: bool):
        # must use "if" because in CurveEditorTimeline._on_live_session, the scrubber _delayed_build_ui() might not finish yet
        if self._scrubber_placer_pill:
            # For some unknown reason, setting self._scrubber_placer_pill.draggable to False causes visual disappear. So set Axis.None instead
            self._scrubber_placer_pill.drag_axis = ui.Axis.X if is_draggable else ui.Axis(0)

    def _set_as_presenter_style(self, is_presenter: bool):
        # to use the {disabled} style conditionally

        # must use "if" because in CurveEditorTimeline._on_live_session, the scrubber _delayed_build_ui() might not finish yet
        if self._scrubber_top:
            self._scrubber_top.enabled = is_presenter
        if self._scrubber_line:
            self._scrubber_line.enabled = is_presenter

    # the only Scrubber._delayed_build_ui() use is in Scrubber.build_ui.
    # add _post_delayed_build_ui after _delayed_build_ui() to do something after the only occasion that _scrubber_placer_pill is created.
    def build_ui(self):
        super().build_ui()
        self._post_delayed_build_ui()

    # use @do_later(wait_frames=1) just the same as _delayed_build_ui(). But that does not ensure build_ui()'s _post_delayed_build_ui() is called really after _delayed_build_ui() (about 1 in 10 fail rate by experiments).
    # so conditionally call _post_delayed_build_ui() inside _post_delayed_build_ui(). OMPE-14440
    @do_later(wait_frames=1)
    def _post_delayed_build_ui(self):
        if self._scrubber_placer_pill:
            is_draggable = not self._get_is_listener()
            self._set_draggable(is_draggable)
            self._set_as_presenter_style(self._get_is_presenter())
        else:
            self._post_delayed_build_ui()
