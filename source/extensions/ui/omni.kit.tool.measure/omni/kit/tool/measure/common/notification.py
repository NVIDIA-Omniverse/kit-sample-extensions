# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = [
    "post_info_notification",
    "post_warn_notification",
    "post_disreguard_future_notification",
]

from typing import Callable

import omni.kit.notification_manager as nm


def __post_notification(message: str, status=nm.NotificationStatus):
    nm.post_notification(message, status=status)


def post_info_notification(message: str) -> None:
    __post_notification(message, nm.NotificationStatus.INFO)


def post_warn_notification(message: str) -> None:
    __post_notification(message, nm.NotificationStatus.WARNING)


def post_disreguard_future_notification(message: str, callback: Callable):
    buttons = [nm.NotificationButtonInfo("OK", None), nm.NotificationButtonInfo("OK - Don't Remind Me", callback)]

    nm.post_notification(message, status=nm.NotificationStatus.INFO, hide_after_timeout=False, button_infos=buttons)
