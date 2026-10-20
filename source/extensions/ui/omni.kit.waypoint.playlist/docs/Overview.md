```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The **omni.kit.waypoint.playlist** extension integrates waypoint navigation into the playlist system. It provides a mechanism to smoothly navigate between configured waypoints while controlling playback actions such as play, next, and previous. The extension ties together playlist models with waypoint transitions, offering an intuitive way to create navigation workflows within the viewport environment.

## Workflow

- **Smooth Transitions:** To navigate between waypoints, users trigger the navigate method which accepts a target waypoint and a transition time parameter (defaulting to 5 seconds). This enables smooth camera movements within the viewport.
- **Playlist Integration:** The extension extends the playlist system by mapping playlist events (such as play, next, and previous) to waypoint actions. This allows users to transition between different scene positions as part of a controlled playlist sequence.

## Configuration

- **Control Settings:** Specific settings are available to enable or disable navigation controls:
  - "next.enabled": Enables the "Play Next" functionality.
  - "previous.enabled": Enables the "Play Previous" functionality.
  - "play.enabled": Toggles the primary play action.
  - "playing": Indicates the current playing status.
- Modifying these settings through the configuration (found under [settings.app.waypoint.playlist] in the extension.toml) directly affects how the playlist navigates between waypoints during operation.

## Relationships

- **Playlist Core Dependency:** The extension builds on the **omni.kit.playlist.core** module by subclassing its playlist models to manage waypoint transitions. The AllWaypointPlaylistModel enhances the playlist system with waypoint-specific data and checks.
- **Waypoint Core Integration:** It incorporates functionality from **omni.kit.waypoint.core** to define and process ViewportWaypoint objects. This integration ensures that navigation commands are executed accurately with respect to the scene’s waypoint definitions.
- **Optional Camera Playlist:** An optional dependency on **omni.kit.tool.camera_playlist** registers the AllWaypointPlaylistModel to the camera playlist tool, further enriching how users interact with the waypoint navigation feature.
