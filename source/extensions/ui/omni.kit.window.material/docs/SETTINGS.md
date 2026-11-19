```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.window.material".stage_has_material_binding_api
- **Default Value**: False
- **Description**: Determines if the stage supports the material binding API, which affects how material bindings are processed on the stage.

### exts."omni.kit.window.material".stage_materials_with_usdrt
- **Default Value**: True
- **Description**: Enables the use of USDRT to retrieve materials from the stage when available.

### exts."omni.kit.window.material".show_capture_thumbnail_menu
- **Default Value**: True
- **Description**: Controls whether the option to capture a thumbnail is shown in the context menu for material items.

### exts."omni.kit.window.material".visible_after_startup
- **Default Value**: False
- **Description**: Specifies if the material browser window should automatically appear immediately after startup.

### exts."omni.kit.window.material".selected.include_children
- **Default Value**: True
- **Description**: Determines whether child primitives are included when evaluating material selections within the stage.

### exts."omni.kit.window.material".data.timeout
- **Default Value**: 5
- **Description**: Sets the timeout value (in seconds) for data operations and asynchronous updates in the material browser.

### exts."omni.kit.window.material".load_after_startup
- **Default Value**: False
- **Description**: Controls whether material data is automatically loaded after the application startup.

### exts."omni.kit.window.material".max_thumbnail_size
- **Default Value**: 512
- **Description**: Defines the maximum pixel size for thumbnails of materials shown in the material browser.

### exts."omni.kit.window.material".min_thumbnail_size
- **Default Value**: 32
- **Description**: Defines the minimum pixel size for thumbnails of materials shown in the material browser.

### exts."omni.kit.window.material".custom_folders
- **Default Value**: []
- **Description**: Allows users to specify a list of custom folder paths for organizing materials within the browser.

### exts."omni.kit.window.material".folders
- **Default Value**: ['Base::http://omniverse-content-production.s3-us-west-2.amazonaws.com/Materials/Base', 'vMaterials::http://omniverse-content-production.s3-us-west-2.amazonaws.com/Materials/vMaterials_2']
- **Description**: Provides default folder paths that are used to populate the material browser with available material libraries.

### exts."omni.kit.window.material".panel_mode
- **Default Value**: ""
- **Description**: Specifies current panel mode. Could be "Library", "Current Stage" "Selected". Default "" means invisible.

## Settings Used by the Extension but Provided by Another Extension
### /persistent/app/window/uiStyle
- **Description**: Specifies the UI style of the application window based on the persistent application settings.
