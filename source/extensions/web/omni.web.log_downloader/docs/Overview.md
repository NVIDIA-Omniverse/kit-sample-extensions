# Web Log Downloader

## Overview

The `omni.web.log_downloader` extension provides functionality for downloading Kit log files via web messaging. This extension enables web clients to request and receive log files from a running Kit instance through Kit's event dispatcher system.

The extension:
- Listens for `request_log_download` events from web clients
- Reads log files from disk (from `/log/file` setting or a custom path)
- Enforces a configurable maximum file size before opening the file
- Returns the entire log file as a single base64-encoded payload
- Delegates wire-level splitting and reassembly to `omni.kit.livestream.messaging`
- Handles errors gracefully with `log_download_error` events

## Features

- **Event-Based Communication**: Uses Kit's Events 2.0 architecture (`carb.eventdispatcher`)
- **Single-Payload Transfer**: Returns the full log file in one `log_download_response` event
- **Transparent Large Message Support**: Large payloads are automatically split and reassembled by `omni.kit.livestream.messaging` — no manual chunking required
- **Base64 Encoding**: Binary log data is base64-encoded for safe transmission over WebRTC
- **File Size Guard**: Two-layer size enforcement prevents unexpected OOMs — a fast stat check in `_download_log` rejects oversized files before any bytes are read, and `read_log_file` applies the same guard independently for direct callers
- **Error Handling**: Comprehensive error reporting via `log_download_error` events
- **Async Processing**: Non-blocking async/await pattern for file I/O; blocking stat and read calls are dispatched off the event loop via `asyncio.to_thread`

## How It Works

### Architecture

```
Web Client                    Kit Extension                  File System
    |                              |                              |
    |---request_log_download------>|                              |
    |                              |---read log file------------->|
    |                              |<------------------------------|
    |                              | (base64-encode full content)  |
    |                              |                              |
    |          omni.kit.livestream.messaging splits payload on wire|
    |<--log_download_response------|                              |
    | (reassembled by client lib)  |                              |
```

### Event Flow

1. **Request**: Web client sends `request_log_download` event
2. **Size check**: Extension stats the file off the event loop; rejects with `log_download_error` if it exceeds `LOG_DOWNLOAD_MAX_SIZE_BYTES`
3. **Processing**: Extension reads the log file off the event loop and base64-encodes its contents
4. **Transfer**: Extension dispatches `log_download_response` with the full payload; `omni.kit.livestream.messaging` handles splitting for large files transparently
5. **Legacy transfer**: Extension also dispatches the deprecated `log_download_start` / `log_download_chunk` / `log_download_complete` sequence for backward compatibility with v1 clients
6. **Error**: If anything fails at any stage, the extension dispatches `log_download_error`

## Event API

### Incoming Events (Extension Listens For)

#### `request_log_download`
Requests a log file download from the Kit instance.

**Payload**:
```python
{
    "log_path": "/path/to/custom/log.txt"  # Optional - uses /log/file setting if omitted
}
```

**Example (from web client)**:
```javascript
// Request default log file
kitMessaging.send("request_log_download", {});

// Request specific log file
kitMessaging.send("request_log_download", {
  log_path: "/path/to/custom/log.txt"
});
```

### Outgoing Events (Extension Sends)

#### `log_download_response`
Sent when the log file has been successfully read. Contains the full file content as a single base64-encoded payload. `omni.kit.livestream.messaging` splits this automatically on the wire if the payload exceeds the WebRTC message size limit, and the client library reassembles it before delivering the event.

**Payload**:
```python
{
    "filename": "kit_20260101_120000.log",  # Basename of the log file
    "content": "base64_string...",          # Full file content, base64-encoded
    "size": 946537,                          # Raw file size in bytes
}
```

#### `log_download_error`
Sent if the download fails at any point.

**Payload**:
```python
{
    "error": "Error description"  # Human-readable error message
}
```

**Common error messages**:
- `"No log file path specified"` — No path provided and `/log/file` setting not configured
- `"Log file not found: /path/to/file"` — File does not exist
- `"Log file too large"` — File exceeds `LOG_DOWNLOAD_MAX_SIZE_BYTES`; payload also includes `size` (actual bytes) and `max` (the limit in bytes)
- `"Failed to read log file: ..."` — Permission or I/O error

## Configuration

### Settings

- **`/log/file`**: Default log file path. If not specified in the request payload, the extension reads this carb setting to determine which log file to download. Kit sets this automatically to the running app's log file.

### Size Limits

File size is enforced at two independent layers, both defaulting to **100 MB**:

| Constant | Location | Purpose |
|---|---|---|
| `LOG_DOWNLOAD_MAX_SIZE_BYTES` | `extension.py` | Extension-level guard; stat is performed off the event loop via `asyncio.to_thread` before any file I/O begins |
| `MAX_LOG_DOWNLOAD_SIZE_BYTES` | `log_download.py` | Module-level guard inside `read_log_file`; protects direct callers (e.g. tests, other extensions) that bypass the extension layer |

To raise or lower the limit, change either constant at import time or patch it in tests.

## Browser-Side Handling

The `content` field arrives base64-encoded. The browser client is responsible for decoding it and triggering a file save. Example JavaScript:

```javascript
kitMessaging.on("log_download_response", (event) => {
    const { filename, content, size } = event.payload;

    // Decode base64 → binary bytes
    const binaryString = atob(content);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }

    // Trigger browser Save File dialog
    const blob = new Blob([bytes], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
});

kitMessaging.on("log_download_error", (event) => {
    console.error("Log download failed:", event.payload.error);
});

// Trigger a download
kitMessaging.send("request_log_download", {});
```

## Manual Testing (Script Editor)

You can test the extension directly from Kit's Script Editor (Window → Script Editor):

```python
import carb
import carb.eventdispatcher
import omni.kit.app

dispatcher = carb.eventdispatcher.get_eventdispatcher()

def on_response(event):
    payload = {str(k): event.payload[k] for k in event.payload.keys()}
    carb.log_warn(f"[TEST] filename={payload.get('filename')}, size={payload.get('size')} bytes")

def on_error(event):
    payload = {str(k): event.payload[k] for k in event.payload.keys()}
    carb.log_error(f"[TEST] error={payload.get('error')}")

sub_response = dispatcher.observe_event(
    observer_name="test.log_downloader.response",
    event_name="log_download_response",
    on_event=on_response,
)
sub_error = dispatcher.observe_event(
    observer_name="test.log_downloader.error",
    event_name="log_download_error",
    on_event=on_error,
)

# Trigger using the app's own log (default)
dispatcher.dispatch_event("request_log_download", payload={})

# Or specify a path explicitly
# dispatcher.dispatch_event("request_log_download", payload={"log_path": "/tmp/some.log"})
```

## Migration from 1.0.0

Version 2.0.0 introduces a new single-payload protocol. The v1 chunked events (`log_download_start`, `log_download_chunk`, `log_download_complete`) are **deprecated but still fire** alongside `log_download_response`, so existing clients continue to work without any changes.

New clients should migrate to `log_download_response` before v3.0.0, when the deprecated events will be removed.

| 1.0.0 (deprecated) | 2.0.0 replacement |
|---|---|
| Listen for `log_download_start` | Listen for `log_download_response` |
| Listen for `log_download_chunk` | *(reassembly handled automatically by `omni.kit.livestream.messaging`)* |
| Listen for `log_download_complete` | *(no equivalent needed — `log_download_response` signals completion)* |
| `transfer_id`, `total_chunks`, `chunk_index` payload fields | *(not needed — single payload requires no tracking)* |
| `data` field (base64 chunk) | `content` field (base64 full file) |

**Before (1.0.0)** — still works, but deprecated:
```javascript
kitMessaging.on("log_download_start",    (e) => { /* init transfer */ });
kitMessaging.on("log_download_chunk",    (e) => { /* accumulate e.payload.data */ });
kitMessaging.on("log_download_complete", (e) => { /* save assembled file */ });
```

**After (2.0.0)** — recommended:
```javascript
kitMessaging.on("log_download_response", (event) => {
    const { filename, content } = event.payload;
    const bytes = Uint8Array.from(atob(content), c => c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], { type: "text/plain" }));
    Object.assign(document.createElement("a"), { href: url, download: filename }).click();
    URL.revokeObjectURL(url);
});
```
