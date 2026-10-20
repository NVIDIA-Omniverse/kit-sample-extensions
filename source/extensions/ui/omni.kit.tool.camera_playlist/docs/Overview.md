```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

**omni.kit.tool.camera_playlist** provides a well-structured interface for managing camera playlists within the Omniverse Kit SDK. Focused on handling camera-specific playlist operations, the extension enables users to organize, retrieve, and manipulate camera playlists through a user interface integrated with USD scenes. Its design centers on offering clear APIs for playlist management without exposing unnecessary complexity.

```{image} ../../../../source/extensions/ui/omni.kit.tool.camera_playlist/icons/preview.png
---
align: center
---
```


## Concepts

- **[Playlist](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.Playlist):** This class encapsulates the functionality to initialize and manage the camera playlist UI. It handles tasks such as toggling the visibility of the playlist window, retrieving the current playlists (with the option to prioritize the active one), adding camera primitives to playlists, and verifying whether a given prim path belongs to a playlist root.
- **[PlaylistManager](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.PlaylistManager):** Acting as the central model for managing both system and user playlists, this class extends an Omni UI abstract item model. It supports adding, removing, cloning, and renaming playlists, while automatically maintaining an ordered list that reflects the latest state.
- **Singleton Access:** The public function [get_instance](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.get_instance) provides a singleton access point to the [Playlist](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.Playlist) instance, ensuring that all components interact with a consistent state.

## Functionality

- **[Playlist](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.Playlist) Operations:** The extension allows the user to retrieve the list of playlists, fetch specific playlist models by name, and add camera primitives to a designated playlist. It also includes functionality to determine whether a given prim path represents a playlist element.
- **Centralized Management:** Through [PlaylistManager](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.PlaylistManager), playlists are centrally managed using operations such as registration, deregistration, cloning, and renaming. The manager also supports integration with USD stages for auto-saving playlist data.
- **UI Integration:** The extension integrates playlists with the UI by managing the corresponding menu items and playlist window, ensuring that users have a seamless interaction experience within the camera context.

## Key Components

- **[Playlist](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.Playlist) Class:**
  - Manages the camera playlist UI and operations.
  - Provides methods to initialize the playlist window and associated menu items on startup, retrieve playlists in a prioritized manner, add camera primitives, and verify playlist root paths.

- **[PlaylistManager](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.PlaylistManager) Class:**
  - Inherits from the Omni UI abstract item model to handle playlist data.
  - Offers methods to register, deregister, append, clone, remove, and rename playlists.
  - Maintains a sorted list of playlist names to reflect updates from both user and system playlists.

- **[get_instance](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.get_instance) Function:**
  - Returns the global instance of the [Playlist](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.Playlist), ensuring that all playlist interactions occur through a consistent singleton interface.

## Relationships

- **Dependencies:**
  - Utilizes **omni.kit.playlist.core** to manage underlying [Playlist](omni.kit.tool.camera_playlist/omni.kit.tool.camera_playlist.Playlist) models and integrate with USD data structures.
  - Relies on **omni.kit.viewport.utility** for viewport-related interactions.
  - Optionally connects with **omni.usd_presenter.sidecar** to enhance USD presentation capabilities when available.

This extension is ideal for users looking to implement a dedicated camera playlist system, providing a focused set of APIs and UI utilities to manage camera playlists effectively with minimal overhead.
