# Changelog

## [0.4.3] - 2026-10-15
- Remove the unused extension-local pip file and nonstandard dependency block. The central migrated-extensions pip manifest owns the existing dedicated bundle.

## [0.4.2] - 2026-08-13
- Rename the toolbar label "Simready Search" to "Search Filters".
- Rename the search mode "AI Mode" to "Natural Language" and "Workspace Cache" to "Tags".
- The "Natural Language" mode now roots the explorer tree at the asset folder inside the mapped index bucket instead of exposing the whole bucket, mirroring the "SimReady" root of the "Tags" mode. Configurable via the new `usd_search_tree_root_subpath` setting (default `Assets/Isaac/6.0/Isaac`).

## [0.4.1] - 2026-08-11
- Add extension version label to the panel footer.
- Proactively add AWS URLs to the S3 collection.
- Handle both S3 and HTTP collections in the tree view.
- Sanitize the search query string passed from the UI to the search model (quote SimReady filters so Kit's search grammar does not reject them).
- Fix: re-assert the "SimReady Search" engine on each TriggerSearch so Kit's per-server engine cache cannot silently fall back to "File Search".
- Add diagnostic logging along the search path.

## [0.4.0] - 2026-07-28
- Redesigned UX:
    - The new search mode selector initializes and activates the asset search mode
    - The explorer tree is proactively filtered based on selected mode & configured S3 buckets
- Fix: leaving the SimReady search mode now clears the content browser search field along with restoring the "File Search" engine.

## [0.3.8] - 2026-06-26
- Rename the "Assets Search" engine to "SimReady Search".
- Fix: "File Search" is now the actual default engine instead of our engine winning the alphabetical fallback; selecting "SimReady Search" now opens the property window on the first click.

- Change extension category to "browsers" and default new icon
## [0.3.7] - 2026-05-14
- Change extension category to "browsers" and default new icon

## [0.3.6] - 2026-05-12
- Add thumbnail icon

## [0.3.5] - 2026-05-11
- Bump simready_search==2026.4.2

## [0.3.4] - 2026-04-30
- Bump simready_search==2026.4.1
- Replace Nucleus temp-download approach with `omni.client.read_file` + `file_reader` argument; removes `_nucleus.py`.
- Fix: `Url` equality and hashing now ignore trailing slashes.
- Fix: WorkspaceCache mode is now also offered for any S3 path ending in "SimReady".
- Fix: Switching browser selection resets all search params, not just the location anchor.
- Fix: profile/feature/tag filters are cleared when switching to AI Search mode.
- Fix: file indexer skips locations that have already been indexed in the current session.
- Hide Tag filter from the WSCache search UI.
- USD Search results capped at 64 (`max_count=64`).
- Switch USD search endpoint and default WSCache S3 URL to production.

## [0.3.3] - 2026-04-21
- Fix an issue with relevance cuttoff value not properly passing to the search library.
- Remove Features & Profiles search parameters from the AI search mode.
- Publish with stripped down pip_prebundle to only include the intermediate dependencies.

## [0.3.2] - 2026-04-17
- GA rc-3

## [0.3.1] - 2026-04-14
- GA rc-2

## [0.3.0] - 2026-04-13
- GA rc-1

## [0.2.3] - 2026-03-05
- S3 and USD Search
- Search mode selector

## [0.2.2] - 2026-02-18
- Delay init search library

## [0.2.1] - 2026-02-17
- Bump search library version

## [0.1.0] - 2026-01-30
### Added
- Init search implementation
