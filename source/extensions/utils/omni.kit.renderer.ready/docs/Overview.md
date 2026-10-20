# omni.kit.renderer.ready

A lightweight, headless extension that logs "RTX ready" when the first rendered frame is delivered. No `omni.ui` dependency — works in headless and cloud-streaming deployments.

## Why This Exists

The existing `omni.kit.viewport.ready` extension couples the "RTX ready" log message with a viewport overlay UI (loading text, progress bar, shader compilation status). For cloud-streaming deployments, operators need the log message to distinguish "stream is broken" from "scene is still loading" — but they don't want the overlay.

This extension provides just the log message with zero UI dependency.

## Usage

Add to your `.kit` file:

```toml
[dependencies]
"omni.kit.renderer.ready" = {}
```

On first rendered frame, you'll see in the log:
```
[51.896s] RTX ready
```

## Configuration

All settings live under /exts/omni.kit.renderer.ready/:

| Setting          | Default     | Description                                  |
| ---------------- | ----------- | -------------------------------------------- |
| autostart        | true        | Start watching immediately on extension load |
| message          | "RTX ready" | The message to log                           |
| stdout           | true        | Also write to stdout (for log scraping)      |
| usd_context_name | ""          | Which UsdContext to watch (empty = default)  |


### Override in your .kit file:

```
[settings.exts."omni.kit.renderer.ready"]
message = "Renderer initialized"
stdout = false
```

## How It Works

1. On startup, subscribes to StageRenderingEventType.NEW_FRAME via carb.eventdispatcher.
2. On first event, logs the timestamped message and unsubscribes.
3. No UI is created. No omni.ui is imported. No viewport overlay.