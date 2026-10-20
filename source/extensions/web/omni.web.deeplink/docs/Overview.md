```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

**omni.web.deeplink** creates sharable deep links that capture the current state of a USD stage including scene location, camera position, timing, and other contextual information. These generated URLs allow users to teleport directly to the exact same location and state within the same stage when opened.

## Setup and Usage

### Prerequisites

This extension works in conjunction with the web streaming library to pass custom messages containing deep link payloads to Kit applications. The Portal Sample passes these custom messages to the Kit app extension via the web streaming library.

### Required Configuration

Before using this extension, you **must** configure the following settings. The default values provided in the extension are placeholders and will not work as-is:

#### 1. Portal Base URL

Set the `portal_base_url` to match your deployed portal URL:

```toml
exts."omni.web.deeplink".portal_base_url = "https://your-portal-domain.com/deeplink/?application=<app-id>&link_data=<link-data>"
```

Replace `https://your-portal-domain.com` with the actual URL where your Portal Sample is deployed. The placeholders `<app-id>` and `<link-data>` should remain as-is in the template - they will be replaced automatically by the extension when generating deeplinks.

Note that the [portal sample](https://github.com/NVIDIA-Omniverse/ov-dgxc-portal-sample) uses /deeplink page for these links, thus it must be contained in the URL pathname for use with the sample.

**Default (placeholder) value:** `"https://portal-id/deeplink/?application=<app-id>&link_data=<link-data>"`

#### 2. Application ID

Set the `application_id` to match the identifier used when publishing your Kit application to the portal:

```toml
exts."omni.web.deeplink".application_id = "your-app-id-123.0.0"
```

This value must match the application ID specified when publishing your Kit app to the portal. See the [Publishing Kit Apps to the Portal documentation](https://docs.omniverse.nvidia.com/omniverse-dgxc/latest/portal-sample/verification.html#publishing-kit-apps-to-the-portal-sample) for more information on application IDs.

**Default (placeholder) value:** `"usd-composer-109.0.1"`

### Configuration Methods

These settings can be configured in several ways:

1. **Kit Configuration File** - Add the settings to your application's `.kit` file:
   ```toml
   [settings]
   exts."omni.web.deeplink".portal_base_url = "https://your-portal.com/deeplink/?application=<app-id>&link_data=<link-data>"
   exts."omni.web.deeplink".application_id = "my-app-1.0.0"
   ```

2. **Command Line Arguments** - Pass settings directly to the executable when launching:
   ```bash
   your-kit-app --/exts/omni.web.deeplink/portal_base_url="https://your-portal.com/deeplink/?application=<app-id>&link_data=<link-data>" --/exts/omni.web.deeplink/application_id="my-app-1.0.0"
   ```

### How It Works

1. **Generating Deeplinks**: When a user creates a deeplink in your Kit application, the extension captures the current scene state and encodes it as a URL using the configured `portal_base_url` and `application_id`.

2. **Receiving Deeplinks**: When a user clicks a deeplink URL in the web portal, the portal sends a custom message to the Kit application containing the deeplink payload.

3. **Applying Deeplinks**: The extension receives the custom message, decodes the scene state data, and restores the captured view.

NOTE: Deep links for OV on DGXC Portal example must lead to the `/deeplink/` page (e.g. `https://your-portal.com/deeplink/?application=<app-id>&link_data=<link-data>`) to redirect the user to a corresponding streaming application.

Requirement: To use this plugin feature, the portal sample used must be version 1.4.0 or later. [See ov-dgxc-portal-sample](https://github.com/NVIDIA-Omniverse/ov-dgxc-portal-sample/blob/main/CHANGELOG.md#version-140---november-2025)

### Related Documentation

- [Publishing Kit Apps to the Portal](https://docs.omniverse.nvidia.com/omniverse-dgxc/latest/portal-sample/verification.html#publishing-kit-apps-to-the-portal-sample) - Learn about application IDs and portal deployment
- [Extension Settings](SETTINGS.md) - Complete list of all configuration options

## Functionality

### Deep Link Generation
The extension captures comprehensive scene state data when creating deep links. Generated links include mandatory information like the current USD stage path and application version, plus optional camera properties and timeline settings based on user preferences.

### Deep Link Application
When a deep link is opened, the extension automatically restores the captured scene state by loading the referenced USD stage, positioning the camera to match the recorded viewpoint, and setting the timeline to the captured time sample. The application process validates the link data structure before applying changes.

### URL Encoding
Deep links use Base64URL encoding to create compact, shareable URLs. The encoded data includes CRC validation to ensure link integrity during transmission and storage.

## Key Components

### LinkGenerator
Captures current scene state from the USD context and stage to build comprehensive deep link data. The generator extracts mandatory scene information and optional camera and time data based on user selection, then encodes this information into a complete URL.

### LinkApplier
Processes incoming deep links and restores the captured scene state asynchronously. The applier validates the decoded data structure, loads the referenced scene, waits for completion, then applies camera transformations and timeline settings.

### Base64URLEncoder
Handles encoding and decoding operations for deep link URLs. The encoder converts dictionary data to Base64URL strings without padding and includes CRC validation to detect corrupted links.

## UI Components

### DeeplinkGenerateWindow
Provides a modal interface for creating deep links with customizable options. Users can choose whether to include camera properties and time information in the generated link. The window validates that the current stage is saved before allowing link generation.

### DeeplinkApplyWindow
Displays incoming deep link information in a readable format and allows users to apply or cancel the deep link operation. The modal window presents the captured scene data and provides confirmation options before restoring the state.

## Configuration

The extension provides several configuration options to customize deep link behavior:

- `portal_base_url` - Template URL for generating complete deep links with application and data parameters
- `default_include_camera` and `default_include_time` - Default selections for including camera and time data
- `clipboard_auto_copy` - Automatically copy generated links to the clipboard
- `show_generate_window` and `show_apply_window` - Control visibility of generation and application windows
- `camera_properties_to_capture` - Specify which camera transform properties to include in links
- `ignore_dirty_state` - Allow link generation from unsaved stages
