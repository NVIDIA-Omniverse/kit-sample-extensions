```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The **omni.kit.property.environment** extension provides property window widgets designed to display and manage environment-related information. It aggregates controls for environment options, date and time, location, weather, and notifications into a single integrated UI widget. The extension tailors its display dynamically based on the selected environment prim, offering a consolidated interface for users to adjust various environment settings.

```{image} ../../../../source/extensions/ui/omni.kit.property.environment/data/preview.png
---
align: center
---
```


## Concepts

- The primary concept is the [EnvironmentPropertyWidget](omni.kit.property.environment/omni.kit.property.environment.EnvironmentPropertyWidget), a specialized property widget built upon a base PropertyWidget from **omni.kit.window.property.**
- It uses discrete UI groups to organize environment properties and adapts its layout depending on the current sky type to enhance user interactivity.

## Functionality

- The widget processes payloads related to environment prim selection, ensuring that only valid payloads update its UI groups.
- It dynamically toggles the visibility and arrangement of control groups such as date/time, location, weather, and notifications based on the relevant environment settings.

## Key Components

- [EnvironmentPropertyWidget](omni.kit.property.environment/omni.kit.property.environment.EnvironmentPropertyWidget)
  The core public API of this module, [EnvironmentPropertyWidget](omni.kit.property.environment/omni.kit.property.environment.EnvironmentPropertyWidget), constructs the UI layout by stacking multiple specialized groups. It manages the environmental property controls and responds to payload updates by refreshing the display accordingly.

## Relationships

- This extension leverages **omni.kit.window.property** for the underlying property widget structure and **omni.kit.property.usd** for handling prim selection payloads.
- It also integrates various UI group components (such as DateTimeGroup, EnvironmentOptionsGroup, LocationGroup, WeatherGroup, and NotificationGroup) to organize the environment-related controls within the widget.
