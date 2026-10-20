```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The Frame Rate Presets in Viewport Menu Bar extension adds a specialized menu item to the viewport’s menu bar that displays frame rate and synchronization presets. This tool provides an easy way to switch between predefined frame pacing modes, helping users manage viewport performance and synchronization in real time. The extension is ready to use immediately once enabled with minimal configuration required.

## Functionality

- **Menu Integration:**  
  The extension registers a dedicated menu container in the viewport’s menubar. This container displays a list of frame rate presets that users can select to control the timing and pacing of the viewport.

- **Preset Management:**  
  The menu offers a range of preset options, including a default mode labeled “No Pacing.” Additionally, if supported hardware is detected, DLSS-G presets will be shown, allowing users to take advantage of advanced synchronization features.

- **User Interaction:**  
  Users can easily click on the menu item to open the preset list, choose a desired frame rate setting, and see the viewport update accordingly. The extension also supports hot key functionality to streamline user workflows.

## Configuration

- **Visibility and Order:**  
  The extension is visible by default and positioned on the right side of the viewport menu bar with a configurable order parameter, ensuring it appears where users expect it.

- **Default Preset Selection:**  
  A default preset ("No Pacing") is applied at startup, which can be adjusted through the extension settings to suit different performance needs.

- **DLSS-G Presets:**  
  An option is available to display DLSS-G presets if the system supports it, enhancing the ability to quickly configure advanced performance modes.

## Relationships

- **Viewport Menubar Core Integration:**  
  The extension builds upon the base menu container provided by the viewport menubar core, ensuring consistency with other viewport menu items.

- **Supporting Dependencies:**  
  It leverages settings from the window preferences module for synchronization presets and window settings to check for DLSS-G support. The inclusion of actions core and hotkeys core facilitates convenient hot key support for rapid preset changes.

This extension enhances the viewport interface by offering a quick-access menu for frame rate presets, making it easier for users to optimize performance without needing to delve into low-level settings.