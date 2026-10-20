# Omniverse Kit Movie Capture

Render and capture the viewport for a single frame or a sequence of them and submit to Omniverse Farms.

# Known Issues
- Changing the viewport resolution during capture will result in the change of the resolution of the images captured. The reason is that movie capture only sets the viewport resolution at the beginning of capture, and doesn't check it during capture.
- The Settle Latency option may affect motion blur results of RT capture. If it happens, try to set Settle Latency to -1 to disable this option and motion blur for RT should work as before.
- Render product dropdown dose not update automatically. If an AOV is created or removed, please close and reopen the movie capture window to get the list refreshed.
- The playlist movie type is experimental and only available when the playlist extension is enabled. We're still working on it and it may not work as expected for now.

# Limitations
- Movie capture doesn't support encode 8K videos.
- Movie capture is designed to capture one viewport for now. We may support multiple-viewport capture in the future.
- Sceneview elements are not captured now due to lack of low level support. We may support it in the future.

#