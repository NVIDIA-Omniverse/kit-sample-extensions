```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

**omni.kit.language.korean** provides Korean language support for Omniverse Kit SDK applications. This extension registers Korean fonts and character regions to enable proper Korean text rendering throughout the application interface.

## Functionality

The extension configures the Korean language settings with appropriate font mappings, scaling factors, and character region definitions. Once loaded, Korean text displays correctly across all Kit interface elements that support internationalization.

**Korean text rendering support includes:**
- Custom font registration for Korean characters
- Character region mapping for Hangul script
- Text scaling adjustments for optimal Korean display
- Integration with the application's text rendering system

## Key Components

### Korean Language Registration

The extension automatically registers Korean language support during startup through the `KoreanLanguageExtension` class. This registration process configures:

- Font selection and fallback handling for Korean characters
- Character encoding and region specifications
- Display scaling parameters optimized for Korean text

The registration integrates with the broader language support system to ensure Korean text renders consistently across different UI components.

## Relationships

This extension depends on `**omni.kit.language.core**`, which provides the foundational language registration system. The Korean extension leverages this core infrastructure to register its specific language configuration and font mappings.

The extension loads early in the application startup sequence to ensure Korean font settings are available before other UI components initialize, guaranteeing proper Korean text rendering from application launch.
