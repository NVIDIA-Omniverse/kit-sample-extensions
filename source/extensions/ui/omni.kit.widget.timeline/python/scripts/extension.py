"""Load submodules of this extension"""

import omni.ext

from .timeline_value_model import *
from .timeline_view import *
from .timeline_view_component import *
from .ui_helpers import *


class TimelineExtension(omni.ext.IExt):
    _ext_id = None
    _icon_path = None

    def __init__(self):
        super().__init__()
        return

    def on_startup(self, ext_id):
        TimelineExtension._ext_id = ext_id
        manager = omni.kit.app.get_app().get_extension_manager()
        extension_path = manager.get_extension_path(ext_id)
        TimelineExtension._icon_path = f"{extension_path}/data/icons"
        return

    def on_shutdown(self):
        return
