"""Provides notification functionality for posting messages to the user interface with customizable display properties."""


def post_notification(message: str, info: bool = False, duration: int = 3):
    """Posts a notification to the user interface.

    Args:
        message (str): The message to display in the notification.
        info (bool, optional): Set to True if the notification is informational; False for a warning. Defaults to False.
        duration (int, optional): The duration in seconds to show the notification. Defaults to 3.
    """
    try:
        import omni.kit.notification_manager as nm

        if info:
            type = nm.NotificationStatus.INFO
        else:
            type = nm.NotificationStatus.WARNING

        nm.post_notification(message, status=type, duration=duration)
    except Exception:
        carb.log_warn(f"Failed to post notification: {message}")
