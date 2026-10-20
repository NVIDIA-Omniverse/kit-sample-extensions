```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.waypoint.core".enable_hotkeys
- **Default Value**: False
- **Description**: Controls whether hotkeys for waypoint operations are enabled.

### exts."omni.kit.waypoint.core".list_window.allow_resize
- **Default Value**: True
- **Description**: Determines if the waypoint list window can be resized by the user.

### exts."omni.kit.waypoint.core".list_window.save_position
- **Default Value**: True
- **Description**: Specifies whether the position of the waypoint list window is preserved between sessions.

### exts."omni.kit.waypoint.core".show_icons
- **Default Value**: True
- **Description**: Toggles the display of waypoint icons within the viewport.

### exts."omni.kit.waypoint.core".omit_prim_visibility_feature
- **Default Value**: True
- **Description**: Indicates if the primitive visibility functionality should be excluded during waypoint processing.

### exts."omni.kit.waypoint.core".recall.disabled_settings
- **Default Value**: Prim Visibility
- **Description**: Defines which settings are disabled during the waypoint recall operation.

### exts."omni.kit.waypoint.core".capture.disabled_settings
- **Default Value**: Prim Visibility
- **Description**: Defines which settings are disabled during the waypoint capture operation.

### exts."omni.kit.waypoint.core".editing_waypoint
- **Default Value**: (empty string)
- **Description**: Stores the name of the waypoint currently being edited.

### exts."omni.kit.waypoint.core".active_waypoint
- **Default Value**: (empty string)
- **Description**: Stores the name of the waypoint that is currently active.

## Settings Used by the Extension but Provided by Another Extension
### app.viewport.currentTool
- **Description**: Specifies the currently active tool within the application, which the waypoint extension monitors to adjust its behavior accordingly.
