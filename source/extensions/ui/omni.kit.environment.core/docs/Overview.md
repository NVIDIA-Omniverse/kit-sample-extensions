```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The **omni.kit.environment.core** extension exposes a set of APIs, widgets, and helpers to configure and manage the environment in a USD stage. It provides functionality for dynamic sky simulation, ground management, and environment property tracking through a collection of player classes, UI components, and utility functions. This extension is designed to streamline operations such as adjusting sun study parameters and applying scene templates.

## Concepts

- **Environment Configuration:** Exposes identifiers, settings, and property models to define multiple environment attributes, including sky type, ground properties, and scene templates.
- **Dynamic Sky and Sun Study:** Supports both dynamic and static sky configurations with dedicated classes to control sun study playback, update time and date, and manage sun position and lighting.
- **Ground Management:** Provides helper APIs to create, bind, and update ground primitives and materials.
- **Property Models:** Implements value models and settings models to monitor USD stage property changes and synchronize UI feedback.

## Functionality

- **Dynamic Sky Simulation:** Users can use the [SunstudyPlayer](omni.kit.environment.core/omni.kit.environment.core.SunstudyPlayer) API and its associated UI widgets (e.g. [PlayButton](omni.kit.environment.core/omni.kit.environment.core.PlayButton), [PlayRateButton](omni.kit.environment.core/omni.kit.environment.core.PlayRateButton), [PlayLoopButton](omni.kit.environment.core/omni.kit.environment.core.PlayLoopButton), [SunstudyTimeSlider](omni.kit.environment.core/omni.kit.environment.core.SunstudyTimeSlider)) to control a dynamic sky that changes over time.
- **Environment Property Adjustment:** The extension exposes models such as [PropertyValueModel](omni.kit.environment.core/omni.kit.environment.core.PropertyValueModel) and [SettingModel](omni.kit.environment.core/omni.kit.environment.core.SettingModel) to dynamically adjust environment parameters including time, date, latitude, and longitude.
- **Scene Template Management:** With [SceneTemplateHelper](omni.kit.environment.core/omni.kit.environment.core.SceneTemplateHelper), users can retrieve, apply, and save scene templates, enabling structured management of environment presets.
- **Ground Rendering:** The [GroundHelper](omni.kit.environment.core/omni.kit.environment.core.GroundHelper) and [GroundType](omni.kit.environment.core/omni.kit.environment.core.GroundType) definitions support creation, detection, and modification of ground primitives, including material re-binding and size adjustments.
- **City Selection UI:** With components like [CityComboBox](omni.kit.environment.core/omni.kit.environment.core.CityComboBox) and [CityModel](omni.kit.environment.core/omni.kit.environment.core.CityModel), the extension efficiently manages geographic data to support predefined locations that influence environment simulation.

## Key Components

- **[SunstudyPlayer](omni.kit.environment.core/omni.kit.environment.core.SunstudyPlayer) & [SunstudySkyType](omni.kit.environment.core/omni.kit.environment.core.SunstudySkyType):** Control the dynamic behavior of the sky by managing play settings and synchronizing property changes for sun positioning.
- **[SkyHelper](omni.kit.environment.core/omni.kit.environment.core.SkyHelper):** Detects sky file types and creates sky primitives (HDRI or dynamic) based on provided URLs.
- **[GroundHelper](omni.kit.environment.core/omni.kit.environment.core.GroundHelper) & [GroundType](omni.kit.environment.core/omni.kit.environment.core.GroundType):** Manage the creation and modification of ground primitives, enabling users to toggle ground rendering modes and adjust sizes.
- **[UsdModelBuilder](omni.kit.environment.core/omni.kit.environment.core.UsdModelBuilder):** Builds and traces USD property models that automatically update with changes, ensuring consistency between environment parameters and stage state.
- **[SceneTemplateHelper](omni.kit.environment.core/omni.kit.environment.core.SceneTemplateHelper):** Offers methods for retrieving and applying scene template URLs, saving template changes, and managing environment prim layers.
- **UI Widgets:** Components such as [Clock](omni.kit.environment.core/omni.kit.environment.core.Clock), [CityComboBox](omni.kit.environment.core/omni.kit.environment.core.CityComboBox), [ResetButton](omni.kit.environment.core/omni.kit.environment.core.ResetButton), [PlayButton](omni.kit.environment.core/omni.kit.environment.core.PlayButton), [PlayLoopButton](omni.kit.environment.core/omni.kit.environment.core.PlayLoopButton), [PlayRateButton](omni.kit.environment.core/omni.kit.environment.core.PlayRateButton), and [SunstudyTimeSlider](omni.kit.environment.core/omni.kit.environment.core.SunstudyTimeSlider) provide interactive controls for users to update and monitor environment settings.

## Configuration

The extension includes several settings that affect its behavior:
- RTX environment options (e.g., auto-loading and default URL for sky assets) determine which environment visuals are used.
- Ground settings like the material path and enable flags control the rendering of ground primitives.
- Sun study parameters that define playback behavior (playing state, rate, loop, current sky path, and type) are configured via dedicated settings.

## Dependencies

This extension leverages other Omniverse Kit modules such as:
- **omni.kit.window.preferences** for integrating preference panels.
- **omni.kit.widget.sliderbar** for the interactive time slider.
- **omni.kit.usd.layers** for operations on the USD stage.
- Additional optional dependencies enhance functionality such as notifications and file picking utilities.

These relationships ensure that the environment core APIs interact smoothly with the rest of the Omniverse Kit ecosystem while providing specialized functionality for environment management.
