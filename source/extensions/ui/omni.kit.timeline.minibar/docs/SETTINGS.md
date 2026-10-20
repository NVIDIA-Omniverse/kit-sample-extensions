```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension

### exts."omni.kit.timeline.minibar".toggleByHover
   - **Default Value**: True
   - **Description**: Controls whether the minibar will show when the mouse hovers over the bottom of the viewport.

### /exts/omni.kit.timeline.minibar/visible
   - **Default Value**: False
   - **Description**: Controls the visibility state of the timeline minibar.

### /exts/omni.kit.timeline.minibar/offsetBottom
   - **Default Value**: 30
   - **Description**: Sets the bottom offset distance for positioning the timeline minibar.

### /exts/omni.kit.timeline.minibar/scale_with_nav_bar
   - **Default Value**: False
   - **Description**: Controls whether the minibar should automatically scale its width based on the navigation bar width.

## Settings Used by the Extension but Provided by Another Extension

### /app/viewport/TimelineMinibar
   - **Description**: Controls the display visibility of the timeline minibar in the viewport and is used to hide the minibar while capturing moving.

### /app/viewport/offsets/navBottom
   - **Description**: Sets the navigation bottom offset in the viewport, which is adjusted when the minibar visibility changes.

### /app/tools/modal_tool_active
   - **Description**: Indicates whether a modal tool is currently active, used to pause timeline and hide minibar when modal tools are engaged.

### /exts/omni.kit.viewport.navigation.core/computed_width
   - **Description**: Provides the computed width of the navigation bar, used for auto-scaling the minibar width when scale_with_nav_bar is enabled.
