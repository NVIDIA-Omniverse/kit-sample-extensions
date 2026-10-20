# Usage Examples

## Get Camera Playlist Instance and Manage Playlists

```python
from omni.kit.tool.camera_playlist import get_instance, PlaylistManager
import omni.usd

# Get the global playlist instance
playlist_instance = get_instance()

# Get the playlist manager instance
manager = PlaylistManager.get_instance()

# Create a new USD stage to work with
usd_context = omni.usd.get_context()
usd_context.new_stage()

# Get list of available playlists
all_playlists = playlist_instance.get_playlists(user_only=False, active_first=True)
print(f"Available playlists: {all_playlists}")

# Get a specific playlist by name
playlist_model = playlist_instance.get_playlist("All Cameras")
if playlist_model:
    print(f"Found playlist: {playlist_model.name}")
```
---

## Work with Playlist Models and Operations

```python
from omni.kit.tool.camera_playlist import PlaylistManager
from omni.kit.playlist.core import SystemPlaylistModel
import omni.usd

# Get the playlist manager
manager = PlaylistManager.get_instance()

# Create a new USD stage
usd_context = omni.usd.get_context()
usd_context.new_stage()

# Get all playlists (user-created only)
user_playlists = manager.get_playlists(user_only=True)
print(f"User playlists: {user_playlists}")

# Create and register a system playlist
system_playlist = SystemPlaylistModel("Custom System Playlist", "camera")
registration_success = manager.register(system_playlist)
print(f"System playlist registered: {registration_success}")

# Clone an existing playlist
if len(manager.playlists) > 0:
    cloned_index = manager.clone("Cloned Playlist", 0)
    print(f"Cloned playlist at index: {cloned_index}")

# Rename a playlist
playlist_to_rename = manager.get_playlist(0)
if playlist_to_rename:
    manager.rename(playlist_to_rename, "Renamed Playlist")
    print(f"Playlist renamed to: {playlist_to_rename.name}")
```
---

## Check Playlist Prims and Load from USD

```python
from omni.kit.tool.camera_playlist import get_instance, PlaylistManager
import omni.usd

# Get instances
playlist_instance = get_instance()
manager = PlaylistManager.get_instance()

# Create a new USD stage
usd_context = omni.usd.get_context()
usd_context.new_stage()
stage = usd_context.get_stage()

# Check if a prim path is a playlist prim
test_path = "/World/Playlists/MyPlaylist"
is_playlist_prim = playlist_instance.is_playlist_prim(test_path)
print(f"Is playlist prim: {is_playlist_prim}")

# Load playlists from USD stage
manager.load_from_usd(stage)
print(f"Loaded playlists: {manager.playlists}")

# Remove a playlist by index
if len(manager.playlists) > 1:
    manager.remove_playlist(len(manager.playlists) - 1)
    print(f"Remaining playlists: {manager.playlists}")
```
---

## Create and Manage Camera Playlists

```python
import asyncio
from omni.kit.tool.camera_playlist import get_instance, PlaylistManager
import omni.kit.commands
import omni.usd

async def create_and_manage_playlists():
    # Get instances
    playlist_instance = get_instance()
    manager = PlaylistManager.get_instance()

    # Create a new USD stage
    usd_context = omni.usd.get_context()
    await usd_context.new_stage_async()

    # Create a camera in the scene
    camera_path = "/camera_01"
    omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Camera", prim_path=camera_path)

    # Get the camera prim
    stage = usd_context.get_stage()
    camera_prim = stage.GetPrimAtPath(camera_path)

    # Add camera to existing playlist
    playlist_instance.add_to_playlist(camera_prim, "All Cameras")

    # Wait for UI updates
    await omni.kit.app.get_app().next_update_async()

    # Create a new custom playlist
    new_playlist_index = manager.append("My Custom Playlist")
    print(f"Created new playlist at index: {new_playlist_index}")

    # Add camera to the new playlist
    playlist_instance.add_to_playlist(camera_prim, "My Custom Playlist")

    # Wait for operations to complete
    await omni.kit.app.get_app().next_update_async()

# Run the async function
asyncio.ensure_future(create_and_manage_playlists())
```
