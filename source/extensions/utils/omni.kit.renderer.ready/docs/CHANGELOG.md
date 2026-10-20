# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com). The project adheres to [Semantic Versioning](https://semver.org).

## [1.0.0] - 2026-05-14
### Added
- Initial release.
- Logs `[Xs] RTX ready` when the first rendered frame is delivered.
- No `omni.ui` dependency — suitable for headless/cloud-streaming use.
- Configurable message text via `/exts/omni.kit.renderer.ready/message`.
- Configurable stdout output via `/exts/omni.kit.renderer.ready/stdout`.
- Watches the default UsdContext by default; configurable via `/exts/omni.kit.renderer.ready/usd_context_name`.
