```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.window.section".menuPath
   - **Default Value**: Tools/Section
   - **Description**: Specifies the menu path where the Section Tool window is inserted within the UI.

### exts."omni.kit.window.section".useSessionLayer
   - **Default Value**: True
   - **Description**: Determines whether section editing operations use the session layer of the USD stage.

### exts."omni.kit.window.section".alwaysDisplay
   - **Default Value**: False
   - **Description**: Controls whether the Section Tool window is always displayed irrespective of automatic UI visibility behaviors.

## Settings Used by the Extension but Provided by Another Extension
### /app/viewport/currentTool
   - **Description**: Specifies the path of the currently active tool, enabling the extension to check and switch tool modes when window visibility changes.

### /rtx/sectionPlane/enabled
   - **Description**: Determines if the section tool is activated on stage, allowing the extension to disable section operations when a stage is opened.

### /rtx/sectionPlane/sectionLight
   - **Description**: Indicates whether section lighting is enabled, affecting how the section is rendered visually in the viewport.

### /rtx/sectionPlane/cutDirection
   - **Description**: Specifies the default cutting direction for sections, thereby controlling the orientation for the section plane.

### /rtx/sectionPlane/plane
   - **Description**: Defines the section plane via a float array representing its equation; this value is updated in response to tool transform changes.

### /rtx/sectionPlane/manipulator
   - **Description**: Controls the visibility of the section manipulator widget, allowing users to interactively adjust the section settings.

### /rtx-defaults/sectionPlane/cutDirection
   - **Description**: Provides the fallback section cutting direction used in RTX workflows, ensuring consistency when no user setting is specified.

### /rtx-defaults/sectionPlane/manipulator
   - **Description**: Specifies the default state of the section manipulator in RTX mode, serving as a baseline configuration for the UI control.

### /exts/omni.kit.window.viewport/showContextMenu
   - **Description**: Manages the visibility of the viewport context menu based on persistent application settings provided by another extension.

### /app/transform/operation
   - **Description**: Controls the current transform operation mode (e.g., "move"), which determines how transformation commands are applied within the application.
