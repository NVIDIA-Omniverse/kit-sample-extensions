```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The **omni.kit.widget.zoombar** extension provides a user interface widget that allows users to adjust zoom levels and switch between icon and detail views. It offers a responsive slider for controlling icon size and buttons to toggle the view mode. This widget is ideal for applications that require a compact and easy-to-use zoom control, especially in file system interfaces.

```{image} ../../../../source/extensions/ui/omni.kit.widget.zoombar/data/preview.png
---
align: center
---
```


## Concepts

- **[ZoomBar](omni.kit.widget.zoombar/omni.kit.widget.zoombar.ZoomBar):** A slider-based control that lets users adjust the zoom level of displayed icons with a configurable range and width. It also features a button to switch between icon and detail views.
- **[FileZoomBar](omni.kit.widget.zoombar/omni.kit.widget.zoombar.FileZoomBar):** Designed to replace the default file picker zoom bar with the same argument interface.

## Functionality

- **Adjustable Zoom Levels:** Users can modify the zoom level via a slider, which supports discrete values mapped to specific zoom ratios.
- **View Mode Toggling:** The widget provides a button that allows switching between icon mode and detail mode. Custom callbacks can be configured to respond to view mode changes.
- **Interactive Feedback:** The [ZoomBar](omni.kit.widget.zoombar/omni.kit.widget.zoombar.ZoomBar) exposes a model property and hover callback functionality, allowing developers to integrate dynamic behaviors and visual responses with minimal effort.

## Key Components

- **[ZoomBar](omni.kit.widget.zoombar/omni.kit.widget.zoombar.ZoomBar) API:**
  - Constructor parameters include slider range (min, max), initial value, slider width, and the current view mode.
  - Developers can attach callbacks for value changes and view mode toggling with clearly defined function signatures.
  - Additional methods like set_on_hovered_fn allow for interaction feedback by handling mouse hover events.

- **[FileZoomBar](omni.kit.widget.zoombar/omni.kit.widget.zoombar.FileZoomBar) API:**
  - Inherits from [ZoomBar](omni.kit.widget.zoombar/omni.kit.widget.zoombar.ZoomBar) and is tailored for file system applications.
  - It retains all the key functionalities of [ZoomBar](omni.kit.widget.zoombar/omni.kit.widget.zoombar.ZoomBar) while enabling a seamless replacement for the existing file picker zoom controls with the same argument configuration.

## Dependencies

- This extension relies on **omni.ui** for its user interface components, ensuring consistency with other Omniverse Kit UI elements. The use of **omni.ui** supports the creation and management of the slider and button widgets.

By focusing on a clear separation of view control and interaction callbacks, **omni.kit.widget.zoombar** provides a practical and flexible zoom interface component for developers looking to enhance file system and icon display functionalities.
