# Changelog

## [0.1.4] - 2026-09-01
- Classify transport failures by exception type as well as message in `RetryingChatModel`; aiohttp raises a bare `asyncio.TimeoutError` whose `str()` is empty, so a gateway timeout matched none of the message patterns (including `"timeout"`) and was retried zero times before failing the run

## [0.1.3] - 2026-08-25
- Widen `RetryingChatModel` backoff to 6 retries with a 45s ceiling; per-model rate limits on the NVIDIA endpoint need ~20-30s of quiet, which the previous 8s ceiling across 3 attempts could never reach

## [0.1.2] - 2026-03-30
- Update the registry logic

## [0.1.1] - 2026-02-27
### Changed
- Update extension dep


## [0.1.0] - 2025-07-03
### Changed
- Starting the extension template
