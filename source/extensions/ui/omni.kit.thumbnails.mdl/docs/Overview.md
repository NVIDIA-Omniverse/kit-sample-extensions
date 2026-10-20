```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

**omni.kit.thumbnails.mdl** is an extension that generates thumbnails for MDL and USD material files. It simplifies the process of creating visual previews by exposing high-level APIs that handle material binding, rendering, and capture operations. The extension is designed to abstract away the complexities of thumbnail generation while ensuring that material appearances are accurately represented.

## Concepts

- The extension differentiates between MDL and USD materials by offering two specialized generators—one for MDL and one for USD.
- Each generator creates a material prim, binds it as required, and then renders the material to produce an image thumbnail that reflects current material settings.

## Functionality

- The [MdlThumbnailGenerator](omni.kit.thumbnails.mdl/omni.kit.thumbnails.mdl.MdlThumbnailGenerator) class is used to generate thumbnails for MDL material files. It binds the appropriate material parameters, applies configured settings like render mode and dimensions, and creates a preview thumbnail.
- The [UsdThumbnailGenerator](omni.kit.thumbnails.mdl/omni.kit.thumbnails.mdl.UsdThumbnailGenerator) class provides similar functionality for USD materials, ensuring a consistent approach to thumbnail capture using designated USD settings.
- The [ThumbnailManager](omni.kit.thumbnails.mdl/omni.kit.thumbnails.mdl.ThumbnailManager) orchestrates thumbnail generation requests. It queues tasks, manages retries in case of timeouts, and ensures that each thumbnail generation task is executed in sequence for reliable results.

## Key Components

- [MdlThumbnailGenerator](omni.kit.thumbnails.mdl/omni.kit.thumbnails.mdl.MdlThumbnailGenerator)
  Generates thumbnails from MDL material files by binding and rendering the material using configurable parameters such as subid, template paths, input prim, render mode, and image size.

- [UsdThumbnailGenerator](omni.kit.thumbnails.mdl/omni.kit.thumbnails.mdl.UsdThumbnailGenerator)
  Provides the capability to generate thumbnails for USD materials. It uses similar logic to bind and capture the material’s appearance, applying settings like render mode and resolution.

- [ThumbnailManager](omni.kit.thumbnails.mdl/omni.kit.thumbnails.mdl.ThumbnailManager)
  Manages and queues thumbnail generation requests. It handles timeouts and implements retry logic to ensure that thumbnail generation proceeds smoothly, even under occasional delays.

## Configuration

- The extension allows configuration of key parameters for both MDL and USD thumbnail generation through settings. Users can specify template paths, input prim identifiers, render modes, and the number of render samples to tailor the thumbnail appearance. These settings influence how the material is bound and rendered before the thumbnail is captured.

## Relationships

- The extension leverages viewport and rendering components (e.g., **omni.kit.viewport.rtx** and **omni.usd**) to capture accurate material visuals. These integrations are vital for ensuring that the generated thumbnails are rendered with the appropriate quality and visual fidelity.
