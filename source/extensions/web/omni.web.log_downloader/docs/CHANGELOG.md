# Changelog

All notable changes to the `omni.web.log_downloader` extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: release event-dispatcher observer guards with reset during shutdown.

## [2.0.0] - 2026-03-11

### Breaking Changes
- `download_log_file_chunked` helper is **removed**; use `read_log_file` instead

### Deprecated
- `log_download_start`, `log_download_chunk`, and `log_download_complete` events are **deprecated** and will be removed in v3.0.0; they continue to fire alongside `log_download_response` for backward compatibility with legacy clients (see Migration from 1.0.0 in Overview)

### Added
- `LOG_DOWNLOAD_MAX_SIZE_BYTES = 100 MB` constant in `extension.py` — extension-level file size guard; stat is performed off the event loop via `asyncio.to_thread` before any bytes are read; oversized files are rejected with a `log_download_error` event containing `error`, `size`, and `max` fields
- `MAX_LOG_DOWNLOAD_SIZE_BYTES = 100 MB` constant in `log_download.py` — module-level guard inside `read_log_file` that protects direct callers (e.g. tests, other extensions) independently of the extension layer

### Changed
- Replaced manual chunked transfer protocol with a single-payload approach; extension now dispatches one `log_download_response` event containing the full base64-encoded log file instead of the previous `log_download_start` / `log_download_chunk` / `log_download_complete` sequence
- Wire-level splitting and reassembly for large files is now handled transparently by `omni.kit.livestream.messaging`, removing the need for manual 40 KB chunking in the extension
- Outbound events (`log_download_response`, `log_download_error`) are now registered with `omni.kit.livestream.messaging` and dispatched via `omni.kit.app.queue_event` instead of `carb.eventdispatcher.dispatch_event`
- Switched dependency from `omni.web.messaging.core` to `omni.kit.livestream.messaging`
- Removed UUID-based transfer IDs — no longer needed since each request produces exactly one response event
- `_download_log` now resolves the log path before performing the size check so a single resolved path is used throughout; `OSError` from the stat is caught and reported as a `log_download_error` separately from the size limit check
- `read_log_file` performs a synchronous `os.path.getsize` check with an isolated `try/except OSError` block before calling `open`; the file is never opened if the size limit is exceeded
- Blocking file read inside `read_log_file` is dispatched off the event loop via `asyncio.to_thread`

### Removed
- `download_log_file_chunked` helper function

## [1.0.0] - 2025-10-31

### Added
- Initial release of web log downloader extension
- Log file download via web messaging interface
- Chunked binary transfer protocol (40KB chunks)
- Support for custom log file paths
- Comprehensive error handling and reporting
- Progress tracking with start, chunk, and completion events
- Automatic integration with Kit logging system

### Features
- Web messaging integration via `omni.web.messaging.core`
- Binary data transfer with base64 encoding
- UUID-based transfer identification
- Concurrent download support
- Settings-based default log path configuration
