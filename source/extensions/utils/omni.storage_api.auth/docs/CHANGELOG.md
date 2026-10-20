# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-27

### Removed
- Content Browser collection UI (`StorageAPICollection`, server tree, popup dialogs)
- Startup polling loop (`pollTimeout`, `pollInterval` settings)
- Legacy single-URL setting `preconfiguredDiscoveryUrl`
- Token caching (`_cached_tokens`, `pop_cached_token()`) — tokens now arrive after auth handle registration

### Added
- `discover_and_register()` — headless auth + discovery via portal messaging
- `auto_mount_preconfigured()` — auto-mount preconfigured URLs sequentially
- Auth status dialog with Cancel support (skips current URL, continues rest)
- Content Browser integration via `connection_manager` (auto-expand on discovery)
- Placeholder fallback for failed URLs with right-click retry
- `authenticationError` event handling from portal
- Portal-driven `auth_timeout` override via `refreshAccessToken` payload
- Thread-safe auth callback with main-loop marshalling for worker threads

### Fixed
- Auth callback reentrancy flag protected with lock
- Failed/canceled discovery state cleaned up for retry
- Auth failures release `omni.client` handles to prevent deadlock
- Singleton auth callback cleaned up in `destroy()`
- Dialog resources properly destroyed on shutdown
- Added timeout dialog for web portal auth timeouts

## [0.1.1] - 2026-03-16
- Added README.md

## [0.1.0] - 2025-02-13
- Initial release: portal-brokered OAuth2 auth for USD Storage API via livestream messaging.
