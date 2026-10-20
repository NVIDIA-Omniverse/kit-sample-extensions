```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension

### exts."omni.web.deeplink".portal_base_url
- **Default Value**: "https://portal-id/deeplink/?application=<app-id>&link_data=<link-data>"
- **Description**: The base URL template for the portal used to generate deeplinks with placeholders for application ID and link data.

### exts."omni.web.deeplink".default_include_camera
- **Default Value**: true
- **Description**: Whether to include camera information by default when generating deeplinks.

### exts."omni.web.deeplink".default_include_time
- **Default Value**: true
- **Description**: Whether to include time information by default when generating deeplinks.

### exts."omni.web.deeplink".clipboard_auto_copy
- **Default Value**: true
- **Description**: Whether to automatically copy generated deeplinks to the clipboard.

### exts."omni.web.deeplink".show_generate_window
- **Default Value**: true
- **Description**: Whether to display the deeplink generation window interface.

### exts."omni.web.deeplink".show_apply_window
- **Default Value**: false
- **Description**: Whether to display the deeplink application window interface.

### exts."omni.web.deeplink".add_file_menus
- **Default Value**: true
- **Description**: Whether to add deeplink-related options to the file menus.

### exts."omni.web.deeplink".add_context_menus
- **Default Value**: true
- **Description**: Whether to add deeplink-related options to context menus.

### exts."omni.web.deeplink".ignore_dirty_state
- **Default Value**: true
- **Description**: Whether to ignore the dirty state of the scene when processing deeplinks.

### exts."omni.web.deeplink".camera_properties_to_capture
- **Default Value**: ["xformOp:translate", "xformOp:rotate", "xformOp:scale", "xformOp:pivot", "xformOp:rotate", "xformOp:transform"]
- **Description**: The list of camera transform properties to capture when including camera information in deeplinks.

### exts."omni.web.deeplink".application_id
- **Default Value**: "usd-composer-109.0.1"
- **Description**: The application identifier used in deeplink generation to specify the target application.

### exts."omni.web.deeplink".wait_for_stage_event_timeout
- **Default Value**: 60.0
- **Description**: The timeout in seconds to wait for stage events when applying a deeplink. This controls how long the extension will wait for the stage to load before timing out.
