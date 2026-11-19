# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import os

import omni.ext
import omni.kit.app
from omni.kit.viewport.registry import RegisterScene

from ..bindings import *
from .bezier_curve_edits_context import BezierCurveEditsContextManager
from .bezier_curve_edits_ui import BezierCurveEditsUI
from .commands import *
from .context_menu import ContextMenu
from .cv_payload import CvPayloadManager
from .menubar_menu import *
from .property_widget_plugin import BasisCurvesCvWidgetPlugin
from .stub_manipulator import CvStubManipulator
from .tool_settings import PencilMenu, PointMenu, SnapMenu, ToolSettingsWindow
from .tools import CurveManipTools


class BezierCurveEditsUIFactory:
    def __init__(self, desc: dict):
        usd_context_name = desc.get("usd_context_name", "")
        context = BezierCurveEditsContextManager.get_context(usd_context_name)
        viewport_api = desc.get("viewport_api")
        self._ui = BezierCurveEditsUI(context, viewport_api)
        self._stub_manip = CvStubManipulator(usd_context_name, viewport_api)

    def destroy(self):
        if self._ui:
            self._ui.destroy()
            self._ui = None
        if self._stub_manip:
            self._stub_manip.destroy()
            self._stub_manip = None

    @property
    def visible(self):
        return True

    @visible.setter
    def visible(self, value):
        pass

    @property
    def categories(self):
        return ("manipulator",)

    @property
    def name(self):
        return "CV Viz"


class BezierCurveEditsUIRegistry:
    def __init__(self):
        super().__init__()
        self._scene = RegisterScene(BezierCurveEditsUIFactory, "omni.curve.manipulator.prim.viz")

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._scene = None


class PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        ToolSettingsWindow.ICON_PATH = os.path.join(ext_path, "data", "icons")

        self._interface = acquire_interface()
        default_context = BezierCurveEditsContextManager.get_context()

        ContextMenu.startup()
        PencilMenu.startup()
        PointMenu.startup()
        SnapMenu.startup()

        self._tools = CurveManipTools()

        # for VP1
        self._bezier_curve_edits_ui = None
        self._setup_vp1_bezier_curve_edits_ui()

        # for VP2
        self._reg = BezierCurveEditsUIRegistry()

        self._menubar_menu = MenubarMenu(default_context.curve_edits)

        self._basis_curves_cv_widget = None

        self._preferences_page = None
        self._widget_registered = False
        manager = omni.kit.app.get_app().get_extension_manager()
        self._pref_hooks = manager.subscribe_to_extension_enable(
            lambda _: self._register_preferences(),
            lambda _: self._unregister_preferences(),
            ext_name="omni.kit.window.preferences",
            hook_name="ManipulatorCV listener",
        )

        self._prop_hooks = manager.subscribe_to_extension_enable(
            lambda _: self._register_property_widget(),
            lambda _: self._unregister_property_widget(),
            ext_name="omni.kit.property.usd",
            hook_name="ManipulatorCV listener",
        )

    def on_shutdown(self):
        self._unregister_preferences()
        self._pref_hooks = None

        self._unregister_property_widget()
        self._prop_hooks = None

        if self._bezier_curve_edits_ui:
            self._bezier_curve_edits_ui.destroy()
            self._bezier_curve_edits_ui = None

        self._menubar_menu.destroy()
        self._menubar_menu = None

        self._reg.destroy()
        self._reg = None

        if self._tools is not None:
            self._tools.destroy()
            self._tools = None

        SnapMenu.shutdown()
        PointMenu.shutdown()
        PencilMenu.shutdown()
        ContextMenu.shutdown()

        BezierCurveEditsContextManager.clear()

        release_interface(self._interface)

    def _register_preferences(self):
        try:
            import omni.kit.window.preferences

            from .preferences_page import Preferences

            self._preferences_page = omni.kit.window.preferences.register_page(Preferences())
        except ImportError:
            pass

    def _unregister_preferences(self):
        try:
            if self._preferences_page:
                import omni.kit.window.preferences

                omni.kit.window.preferences.unregister_page(self._preferences_page)
                self._preferences_page = None
        except ImportError:
            pass

    def _register_property_widget(self):
        try:
            if not self._widget_registered:
                import omni.kit.window.property

                from .property_widget import BasisCurvesCvWidget, BasisCurvesSchemeDelegate, BasisCurvesWidget

                pw = omni.kit.window.property.get_window()
                context = BezierCurveEditsContextManager.get_context()
                self._basis_curves_cv_widget = BasisCurvesCvWidget()
                pw.register_widget("prim", "basis_curves", BasisCurvesWidget(context.curve_edits))
                pw.register_widget(
                    CvPayloadManager.PROPERTY_PANEL_NAME,
                    CvPayloadManager.PROPERTY_PANEL_NAME,
                    self._basis_curves_cv_widget,
                )

                # This might not actually work because omni.kit.property.bundle calls set_scheme_delegate_layout which doesn't include basis_curves_prim delegate
                # Ideally the Create App should call set_scheme_delegate_layout to handle all included delegates.
                # TODO move omni.kit.property.bundle or set_scheme_delegate_layout to Create App
                pw.register_scheme_delegate("prim", "basis_curves_prim", BasisCurvesSchemeDelegate())

                self._widget_registered = True
        except ImportError:
            ...

    def _unregister_property_widget(self):
        try:
            if self._basis_curves_cv_widget:
                import omni.kit.window.property

                omni.kit.window.property.get_window().unregister_widget(
                    CvPayloadManager.PROPERTY_PANEL_NAME,
                    CvPayloadManager.PROPERTY_PANEL_NAME,
                    self._basis_curves_cv_widget,
                )

                self._basis_curves_cv_widget.clean()
                self._basis_curves_cv_widget = None

            if self._widget_registered:
                import omni.kit.window.property

                pw = omni.kit.window.property.get_window()

                pw.unregister_scheme_delegate("prim", "basis_curves_prim")
                pw.unregister_widget("prim", "basis_curves")
                pw.unregister_widget(CvPayloadManager.PROPERTY_PANEL_NAME, CvPayloadManager.PROPERTY_PANEL_NAME)

                self._widget_registered = False
        except ImportError:
            pass

    def _setup_vp1_bezier_curve_edits_ui(self):
        default_context = BezierCurveEditsContextManager.get_context()
        self._bezier_curve_edits_ui = BezierCurveEditsUI(default_context)

        async def setup_async():
            try:
                await omni.kit.app.get_app().next_update_async()

                import omni.kit.viewport_legacy as vp

                vp.acquire_viewport_interface()
            except:
                self._bezier_curve_edits_ui.destroy()
                self._bezier_curve_edits_ui = None

        asyncio.ensure_future(setup_async())
