import gc

import omni.anim.curve.core
import omni.ext
import omni.kit.commands

from . import commands
from . import curve_editor_globals as globals

# these imported classes have sington for extension to handle
from .curve_editor import SingletonCurveEditor
from .curve_editor_view import CurveEditorWindow
from .timeline_merge_core_settings import TimelineMergeCoreSettings
from .timeline_merge_style import TimelineMergeStyle


class CurveEditorExtension(omni.ext.IExt):
    def on_startup(self, ext_id):

        globals.curve_plugin = omni.anim.curve.core.acquire_interface()

        omni.kit.commands.register_all_commands_in_module(commands)

        self._curve_editor_window = CurveEditorWindow()
        self._curve_editor_window.on_startup(ext_id)

    def on_shutdown(self):
        # At the time of the comment, TimelineView has internal circular reference of objects and __del__(), so gc can not handle. Call destroy first to break the circular reference, as a workaround.
        self._curve_editor_window._view._timeline_view.destroy()

        self._curve_editor_window.on_shutdown()
        self._curve_editor_window = None

        # singletons destroy
        SingletonCurveEditor.destroy()
        TimelineMergeCoreSettings.destroy()
        TimelineMergeStyle.destroy()

        omni.kit.commands.unregister_module_commands(commands)

        omni.anim.curve.core.release_interface(globals.curve_plugin)
        globals.curve_plugin = None

        gc.collect()

        # use for debugging memory problem.
        # objgraph.show_backrefs([some_weak_pointer_stored_before_collect,...], filename='d:\sample-graph.png')
