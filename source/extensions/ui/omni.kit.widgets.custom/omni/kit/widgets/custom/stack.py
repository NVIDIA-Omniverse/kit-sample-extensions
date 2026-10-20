# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui


# A ZStack that will block mouse events to deeper
class OpaqueZStack(ui.ZStack):
    def __init__(self, **kwargs):
        kwargs["opaque_for_mouse_events"] = True
        if "mouse_pressed_fn" not in kwargs:
            kwargs["mouse_pressed_fn"] = lambda *_: self._dummy()

        super().__init__(**kwargs)

    def _dummy(self):
        pass
