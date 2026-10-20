# Usage Examples

## Create and Configure a Playlist

```python
from omni.kit.playlist.core import PlaylistModel, PlayMode, enum_playlist_cards

# Create a new playlist with smooth transitions
playlist = PlaylistModel(
    name="My Camera Playlist",
    transition_type=PlayMode.TRANSITION_SMOOTH,
    transition_time=2.0,  # 2 seconds transition between cameras
    item_time=5.0,        # Display each camera for 5 seconds
)

# Load available camera cards from the stage
camera_cards = enum_playlist_cards()

# Add camera cards to the playlist
for card in camera_cards:
    playlist.insert_item(card)

print(f"Created playlist '{playlist.name}' with {len(playlist.items)} cameras")
```
---

## Play a Playlist with PlaylistPlayer

```python
from omni.kit.playlist.core import PlaylistModel, PlaylistPlayer, PlayMode

# Create a playlist with cut transitions
playlist = PlaylistModel(
    name="Quick Camera Tour",
    transition_type=PlayMode.TRANSITION_CUT,
    item_time=3.0
)

# Add some camera cards (assuming they exist in the scene)
from omni.kit.playlist.core import enum_playlist_cards
cards = enum_playlist_cards()
for card in cards[:3]:  # Add first 3 cameras
    playlist.insert_item(card)

# Define callback functions
def on_started():
    print("Playlist playback started!")

def on_stopped():
    print("Playlist playback stopped!")

def on_playing(index):
    print(f"Now playing camera at index: {index}")

# Create and start the player
player = PlaylistPlayer.create(
    playlist=playlist,
    start=0,
    on_started_fn=on_started,
    on_stopped_fn=on_stopped,
    on_playing_fn=on_playing
)

# Start playback
if player.play():
    print("Playback started successfully")
else:
    print("Failed to start playback")
```
---

## Use PlayManager for Advanced Playlist Control

```python
from omni.kit.playlist.core import get_play_manager, PlaylistModel, PlayMode, enum_playlist_cards

# Get the global play manager
play_manager = get_play_manager()

# Create a playlist
playlist = PlaylistModel(
    name="Main Playlist",
    transition_type=PlayMode.TRANSITION_SMOOTH,
    transition_time=1.5,
    item_time=4.0
)

# Add cameras to playlist
cards = enum_playlist_cards()
for card in cards:
    playlist.insert_item(card)

# Set up callbacks
def on_playlist_changed(playlist_name):
    print(f"Now playing playlist: {playlist_name}")

def on_item_changed(card_item):
    print(f"Current item changed to: {card_item.name}")

# Subscribe to events
playlist_sub = play_manager.subscribe_playing_playlist_changed(on_playlist_changed)
item_sub = play_manager.subscribe_current_playlist_item_changed(on_item_changed)

# Set current playlist and start playback
play_manager.current_playlist = playlist
play_manager.play()

# Stop playback
play_manager.stop()
```
---

## Create System Playlist for Camera Management

```python
from omni.kit.playlist.core import SystemPlaylistModel, PlaylistCard, PlayMode

# Create a system playlist for all cameras
system_playlist = SystemPlaylistModel(
    name="All Scene Cameras",
    camera_type=PlaylistCard.CAMERA
)

# System playlists automatically populate with cameras
system_playlist.check_update()

print(f"System playlist contains {len(system_playlist.items)} cameras")
print(f"Playlist is system-managed: {system_playlist.system}")
print(f"Playlist can be changed: {system_playlist.can_change}")

# Configure playback settings
system_playlist.transition_type = PlayMode.TRANSITION_CUT
system_playlist.transition_time = 1.0
system_playlist.item_time = 3.0

# Access playlist items
items = system_playlist.get_item_children()
if items:
    # Select first camera
    system_playlist.selection = items[0]

    # Navigate through cameras
    next_index = system_playlist.next()
    prev_index = system_playlist.previous()

    print(f"Selected camera: {system_playlist.selection.name}")
```
