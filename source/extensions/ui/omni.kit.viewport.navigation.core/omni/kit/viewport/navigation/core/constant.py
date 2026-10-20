from pathlib import Path

IMAGE_SIZE = 43

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.core/"
NAVIGATION_TOOL_BOTTOM_OFFSET = SETTINGS_ROOT + "bottom_offset"
NAVIGATION_TOOL_BOTTOM_SPACING = SETTINGS_ROOT + "bottom_spacing"
NAVIGATION_IS_LARGE = SETTINGS_ROOT + "is_large"
NAVIGATION_LARGE_SIZE = SETTINGS_ROOT + "large_size"
NAVIGATION_SMALL_SIZE = SETTINGS_ROOT + "small_size"
NAVIGATION_COMPUTED_WIDTH = SETTINGS_ROOT + "computed_width"
CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data/tests")

# Forward compatible with omni.kit.tool.navigation Settings
VIEWPORT_DISPLAY_OPTIONS_PATH = "/persistent/app/viewport/displayOptions"
SETTING_NAVIGATION_ROOT = "/exts/omni.kit.viewport.navigation.core/"
NAVIGATION_TOOL_OPERATION_ACTIVE = SETTING_NAVIGATION_ROOT + "activeOperation"
NAVIGATION_IS_VISIBLE = SETTING_NAVIGATION_ROOT + "isVisible"

SETTINGS_PATH_MODAL_TOOL_ACTIVE = "/app/tools/modal_tool_active"
VIEWPORT_TOOLS_BOTTOM_OFFSET_PATH = "/app/viewport/offsets/navBottom"

NAVIGATION_HOTKEYS_ENABLED = SETTINGS_ROOT + "enable_hotkeys"
NAVIGATION_NEXT_OPERATION = SETTINGS_ROOT + "next_operation"
NAVIGATION_NEXT_OPERATION_HOTKEY = SETTINGS_ROOT + "hotkey_next_operation"
