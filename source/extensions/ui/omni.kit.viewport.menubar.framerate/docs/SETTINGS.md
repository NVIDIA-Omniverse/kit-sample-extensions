```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension

### exts."omni.kit.viewport.menubar.framerate".showDLSSG
   - **Default Value**: True
   - **Description**: Determines whether DLSSG options should be shown in the viewport's framerate menubar.

### exts."omni.kit.viewport.menubar.framerate".currentPreset
   - **Default Value**: No Pacing
   - **Description**: Specifies the current framerate preset that is active in the viewport menubar.

### exts."omni.kit.viewport.menubar.framerate".order
   - **Default Value**: 90
   - **Description**: Controls the ordering of the framerate menu item within the extension’s menu layout.

### exts."omni.kit.viewport.menubar.framerate".visible
   - **Default Value**: True
   - **Description**: Toggles the visibility of the framerate menubar in the viewport.

## Settings Used by the Extension but Provided by Another Extension

### /rtx-transient/internal/dlssg/supported
   - **Description**: Indicates whether DLSSG support is available, which is used to decide if DLSSG-related presets should be displayed.

### /rtx/rendermode
   - **Description**: Holds the current rendering mode of the viewport, affecting how frame pacing presets are applied.

### /persistent/app/viewport/defaults/tickRate
   - **Description**: Specifies the default tick rate for the viewport that is intentionally skipped during preset application as it has no effect after viewport creation.

### /rtx-transient/dlssg/enabled
   - **Description**: Determines if DLSSG-specific functionality is enabled within a preset, affecting whether those presets should be considered for display.
