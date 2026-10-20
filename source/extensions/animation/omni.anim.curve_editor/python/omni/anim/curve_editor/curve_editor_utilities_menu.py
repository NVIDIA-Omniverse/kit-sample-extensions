import weakref

import carb
import omni.ext
import omni.kit.commands
import omni.kit.context_menu
import omni.kit.notification_manager as nm
import omni.ui as ui
import omni.usd


class CurveEditorUtilitiesMenu:
    def __init__(self, view):
        self._view = weakref.ref(view)
        self._register_context_menu()

    def destroy(self):
        self._view = None
        self._parent_frame = None
        self._anim_preferences_menu = None
        self._simplify_curve_menu = None

    def build_ui(self, parent_frame):
        self._parent_frame = parent_frame

    def show(self):
        # get context menu core functionality & check its enabled
        context_menu = omni.kit.context_menu.get_instance()
        if context_menu is None:
            return

        # setup objects, this is passed to all functions
        objects = {}

        menu_list = omni.kit.context_menu.get_menu_dict("options", "omni.anim.curve_editor")

        # show menu
        context_menu.show_context_menu("options", objects, menu_list)

    def _on_simplifye_curve(self, obj):
        from omni.anim.curve.ui import get_instance

        ui_instance = get_instance()
        ui_instance._simplification_menu._show_menu(None, None)

    def _on_anim_preference(self, obj):
        try:
            from omni.kit.preferences.animation.animation_preferences import AnimationPreferences
            from omni.kit.window.preferences import select_page, show_preferences_window
        except ModuleNotFoundError:
            carb.log_warn("Please turn on extension omni.kit.window.preferences & omni.kit.preferences.animation")
            nm.post_notification(
                "Please turn on extension omni.kit.window.preferences & omni.kit.preferences.animation",
                status=nm.NotificationStatus.WARNING,
                duration=5,
            )
            return
        show_preferences_window()
        select_page(AnimationPreferences)

    def _register_context_menu(self):
        context_menu = omni.kit.context_menu.get_instance()
        if context_menu:
            simplify_curve_menu = {
                "name": "Simplify Curve",
                "onclick_fn": self._on_simplifye_curve,
            }
            self._simplify_curve_menu = omni.kit.context_menu.add_menu(
                simplify_curve_menu, "options", "omni.anim.curve_editor"
            )

            anim_preferences_menu = {
                "name": "Anim Preferences",
                "onclick_fn": self._on_anim_preference,
            }
            self._anim_preferences_menu = omni.kit.context_menu.add_menu(
                anim_preferences_menu, "options", "omni.anim.curve_editor"
            )
