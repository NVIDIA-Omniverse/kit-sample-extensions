import omni.ext
from omni.genproc.core import *

from .scripts.commands import *
from .scripts.curve_deformer_menu import CurveDeformerMenu
from .scripts.curve_zone_sign_menu import CurveZoneSignMenu
from .scripts.genproc_actions import deregister_actions, register_actions
from .scripts.menu import Menu


class PublicExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        # TODO: we should consolidate menu and curve_deformer_menu...
        self._menu = None
        self._curve_deformer_menu = None

    def on_startup(self, ext_id):
        self._interface = acquire_interface()
        self._menu = Menu()
        self._curve_deformer_menu = CurveDeformerMenu()
        self._curve_zone_sign_menu = CurveZoneSignMenu()

        self._ext_id_no_version = ext_id.split("-")[0]
        register_actions(self._ext_id_no_version, CurveDeformerMenu, lambda: self._menu)

    def on_shutdown(self):
        deregister_actions(self._ext_id_no_version)

        self._curve_zone_sign_menu.on_shutdown()
        self._curve_zone_sign_menu.on_shutdown = None
        self._curve_deformer_menu.on_shutdown()
        self._curve_deformer_menu = None
        self._menu.on_shutdown()
        self._menu = None

        release_interface(self._interface)
