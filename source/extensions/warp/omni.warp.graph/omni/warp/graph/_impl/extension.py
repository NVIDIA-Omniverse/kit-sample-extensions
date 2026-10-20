# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Entry point for the extension."""

import asyncio
import importlib
import os
from typing import (
    Callable,
    Sequence,
)

import carb
import carb.dictionary
import omni.ext
import omni.graph.core as og
import omni.stageupdate
import omni.usd

EXT_ID = "omni.warp.graph"


#   Kernel Node
# ------------------------------------------------------------------------------

try:
    from omni.kit.window.popup_dialog import MessageDialog

    KERNEL_NODE_HAS_POPUP_DIALOG_EXT = True
except ImportError:
    KERNEL_NODE_HAS_POPUP_DIALOG_EXT = False


# Whether kernel node content can be trusted and evaluated.
# If unset, opening a scene with Warp kernel nodes prompts the user
# to enable them for that scene in the current session.
# When disabled, evaluation of graphs containing these nodes stops.
KERNEL_NODE_SETTING_ENABLE = "/app/omni.warp.graph/kernel_node_enable"

# Kernel node types that need to be checked.
KERNEL_NODE_TYPES = (f"{EXT_ID}.Kernel",)

# Opt-in prompt message.
KERNEL_NODE_PROMPT_MSG = """This stage contains Warp kernel nodes.

There is currently no limitation on what code can be executed by this node. \
This means that graphs that contain these nodes should only be used when \
the author of the graph is trusted.

Do you want to enable the Warp kernel node functionality for this session?
"""

# Stage URLs that the user has enabled for the current session.
KERNEL_NODE_ENABLED_STAGE_URLS = set()


def kernel_node_find_graphs() -> Sequence[og.Graph]:
    """Find all the graphs containing kernel nodes."""
    return tuple(
        g
        for g in og.get_all_graphs()
        if any(n.get_node_type().get_node_type() in KERNEL_NODE_TYPES for n in g.get_nodes())
    )


def kernel_node_prompt_user(on_enable_cb: Callable):
    """Prompt the user to device whether to enable kernel nodes."""

    def on_cancel(dialog: MessageDialog):
        dialog.hide()

    def on_ok(dialog: MessageDialog):
        on_enable_cb()
        dialog.hide()

    dialog = MessageDialog(
        title="Warning",
        width=400,
        message=KERNEL_NODE_PROMPT_MSG,
        ok_handler=on_ok,
        ok_label="Yes",
        cancel_handler=on_cancel,
        cancel_label="No",
    )

    async def show_async():
        import omni.kit.app

        # Wait for a few frames to allow the app UI to finish loading.
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        dialog.show()

    asyncio.ensure_future(show_async())  # noqa: RUF006


def kernel_node_on_enable(stage_url: str, graphs: Sequence[og.Graph]) -> None:
    """Action to take if the user decides to enable kernel nodes."""

    def fn():
        for graph in graphs:
            graph.set_disabled(False)

        KERNEL_NODE_ENABLED_STAGE_URLS.add(stage_url)

    return fn


def kernel_node_verify(stage_url: str) -> None:
    """Check for kernel node instances and confirm user wants to run them."""
    if stage_url in KERNEL_NODE_ENABLED_STAGE_URLS:
        # The user previously enabled evaluation for that scene.
        return

    settings = carb.settings.get_settings()
    if settings.is_accessible_as(
        carb.dictionary.ItemType.BOOL,
        KERNEL_NODE_SETTING_ENABLE,
    ):
        # Enforce the setting by disabling graphs as necessary.
        if not settings.get(KERNEL_NODE_SETTING_ENABLE):
            for graph in kernel_node_find_graphs():
                graph.set_disabled(True)

        return

    # The setting is not present, retrieve any graph in the scene
    # containing kernel nodes.
    graphs = kernel_node_find_graphs()
    if not graphs:
        return

    # Disable these graphs until the user answer the prompt.
    for graph in graphs:
        graph.set_disabled(True)

    if not KERNEL_NODE_HAS_POPUP_DIALOG_EXT:
        # Prompting not available in headless mode, keep the graphs disabled.
        carb.log_warn(
            "Some graphs in the current stage have been disabled "
            "due to containing Warp kernel nodes. Enable them with "
            "--/app/omni.warp.graph/kernel_node_enable=true."
        )
        return

    # Prompt the user.
    on_enable_cb = kernel_node_on_enable(stage_url, graphs)
    kernel_node_prompt_user(on_enable_cb)


#   Entry Point
# ------------------------------------------------------------------------------


OMNIGRAPH_STAGEUPDATE_ORDER = 100


def on_stage_attach(stage_id: int, meters_per_unit: float) -> None:
    stage_ctx = omni.usd.get_context_from_stage_id(stage_id)
    stage_url = stage_ctx.get_stage_url()
    kernel_node_verify(stage_url)


class Extension(omni.ext.IExt):
    def __init__(self, *args, **kwargs):
        import omni.kit.app

        super().__init__(*args, **kwargs)
        self._stage_sub = None

        app = omni.kit.app.get_app()
        manager = app.get_extension_manager()

        if manager.is_extension_enabled("omni.graph.ui"):
            # importlib avoids static import analysis (e.g. repo checkapi) loading
            # omni.graph.ui, which circularly imports omni.kit.property.usd.
            graph_ui = importlib.import_module("omni.graph.ui")
            here = os.path.dirname(os.path.abspath(__file__))
            nodes_init_path = os.path.join(here, "__init__.py")
            graph_ui.ComputeNodeWidget.get_instance().add_template_path(nodes_init_path)

    def on_startup(self, ext_id):
        settings = carb.settings.get_settings()

        stage_update = omni.stageupdate.get_stage_update_interface()
        self._stage_sub = stage_update.create_stage_update_node(
            EXT_ID,
            on_attach_fn=on_stage_attach,
        )
        stage_sub_node_idx = len(stage_update.get_stage_update_nodes()) - 1
        assert self._stage_sub

        # Run the subscription after OmniGraph nodes have been instantiated.
        stage_update.set_stage_update_node_order(
            stage_sub_node_idx,
            OMNIGRAPH_STAGEUPDATE_ORDER + 1,
        )

    def on_shutdown(self):
        self._stage_sub = None
