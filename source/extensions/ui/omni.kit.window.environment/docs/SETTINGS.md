```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.window.environment".visible_after_startup
   - **Default Value**: False
   - **Description**: Controls whether the Environments window is shown immediately after startup by checking its boolean value in the extension’s startup routine.

### exts."omni.kit.window.environment".data.timeout
   - **Default Value**: 30
   - **Description**: Sets the timeout value (in seconds) used by the environment browser model when retrieving data.

### exts."omni.kit.window.environment".load_after_startup
   - **Default Value**: False
   - **Description**: Determines whether the environment data should automatically be loaded after startup, influencing the initial state of the window.

### exts."omni.kit.window.environment".custom_folders
   - **Default Value**: []
   - **Description**: Provides a list of custom folder paths that can be used by the environment browser model as additional collection roots.

### exts."omni.kit.window.environment".folders_hide_in_category
   - **Default Value**: ['2023_1']
   - **Description**: Specifies a list of folder category identifiers to hide from the UI in the environment browser.

### exts."omni.kit.window.environment".folders
   - **Default Value**: ['https://omniverse-content-production.s3.us-west-2.amazonaws.com/Environments/2023_1']
   - **Description**: Defines the default environment folder collection root URL used by the browser to load available environments.

## Settings Used by the Extension but Provided by Another Extension
### /app/warmupMode
   - **Description**: A boolean flag checked during startup to determine if the application is in warmup mode, which in turn triggers a warmup model for the environment browser.

### /persistent/app/window/uiStyle
   - **Description**: Specifies the UI style (e.g., "NvidiaDark" or "NvidiaLight") for the application’s persistent window, which is used by the style function to set various UI element colors and properties.
