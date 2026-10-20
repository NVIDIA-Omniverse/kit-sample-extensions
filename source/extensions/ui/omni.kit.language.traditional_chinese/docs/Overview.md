```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

**omni.kit.language.traditional_chinese** provides Traditional Chinese font support for Omniverse Kit. This extension registers Traditional Chinese as a supported language within the Omniverse language system, enabling proper display and rendering of Traditional Chinese characters throughout the application interface.

## Functionality

The extension integrates Traditional Chinese font capabilities into Omniverse Kit's localization framework. When loaded, it registers the Traditional Chinese language with the system, allowing applications to properly render Traditional Chinese text and characters across UI elements, menus, and other interface components.

The extension is configured to load early in the startup sequence to ensure font settings are properly established before other UI components initialize. This early loading prevents potential text rendering issues that could occur if the font registration happened after UI elements were already created.

## Relationships

This extension depends on **omni.kit.language.core**, which provides the foundational language registration and management system. The Traditional Chinese extension uses this core infrastructure to register itself as an available language option within the Omniverse Kit language framework.
