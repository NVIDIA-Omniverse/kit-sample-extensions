```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

**omni.kit.timeline.minibar** provides a compact playback toolbar that displays at the bottom of viewport windows. This extension integrates timeline controls directly into the viewport interface, allowing users to control playback without needing to access separate timeline windows.

```{image} ../../../../source/extensions/ui/omni.kit.timeline.minibar/data/preview.png
---
align: center
---
```


## Functionality

The minibar displays essential timeline controls including play, pause, stop, and frame navigation buttons in a minimized interface that overlays the viewport. Users can control timeline playback while maintaining focus on their viewport content.

The extension provides hover-based activation, where the minibar automatically appears when the mouse hovers over the bottom edge of the viewport. This design keeps the interface clean while ensuring playback controls remain accessible.

## Configuration

### Settings Paths

The extension exposes three configuration paths for controlling minibar visibility and behavior:

- `MINIBAR_VISIBLE_PATH`: Controls the overall visibility of the minibar
- `MINIBAR_BOTTOM_SETTINGS_PATH`: Manages bottom positioning settings
- `MINIBAR_TOGGLE_BY_HOVER_PATH`: Controls hover-based activation behavior

These paths allow other extensions or applications to programmatically control minibar behavior and integrate it into custom viewport configurations.

## Relationships

The extension builds on **omni.timeline** for core timeline functionality and integrates with **omni.kit.viewport.registry** to embed controls within viewport instances. It optionally works with **omni.timeline.live_session** for collaborative timeline control and **omni.kit.viewport.menubar.display** for enhanced viewport UI integration.
