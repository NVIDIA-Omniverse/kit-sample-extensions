# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Reset variant editor and related UI between tests so ordering is irrelevant."""

import omni.kit.app
import omni.kit.ui_test as ui_test

from ..core import VariantEditorCore
from ..extension import get_window
from ..stage_change_helper import StageChangeHelper


async def reset_variant_editor_test_state(*, restore_auxiliary_ui: bool = True) -> None:
    """Hide the variant editor, clear singleton core/tree state, and undo common UI mutations."""
    if restore_auxiliary_ui:
        try:
            ui_test.find("Property").window.visible = True
        except Exception:
            pass
        try:
            from omni.kit.window.content_browser.test_helper import ContentBrowserTestHelper

            await ContentBrowserTestHelper().toggle_grid_view_async(False)
        except Exception:
            pass

    w = get_window()
    if w is None:
        return

    w.hide()
    core = VariantEditorCore.get_instance()
    core.authoring_variant = 0
    core.create_visibility_by_default = True
    core._clear_all()
    vtm = getattr(w, "_variant_tree_model", None)
    if vtm is not None:
        vtm.clear()
    StageChangeHelper.disable()
    await omni.kit.app.get_app().next_update_async()
