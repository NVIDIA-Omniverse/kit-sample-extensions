# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.9.10] - 2026-05-13
### Changed
- Migrated `apply_deeplink_request` handling to pure Events 2.0: subscribe via `carb.eventdispatcher.observe_event` and dispatch via `dispatch_event`; removed the Events 1.0 message-bus alias bridge (`carb.events.type_from_string` + `omni.kit.app.register_event_alias` + `message_bus.dispatch`).
- Removed the incorrect `omni.kit.livestream.messaging.register_event_type_to_send` call for the inbound `apply_deeplink_request` event; that helper only applies to outgoing events. Inbound livestream events are re-dispatched directly under their original event name by `omni.kit.livestream.messaging`.
- Tests now dispatch `apply_deeplink_request` via `carb.eventdispatcher.get_eventdispatcher().dispatch_event(...)` instead of `get_message_bus_event_stream().dispatch(...)`.

## [0.9.9] - 2026-02-20
### Changed
- OMPE-78181: Fixed issue with stages not having bound camera metadata

## [0.9.8] - 2026-01-22
### Changed
- OMPE-78181: Fix for camera getting reset during loading due to timeout

## [0.9.7] - 2026-01-14
### Changed
- OMPE-77213: Updated docs

## [0.9.6] - 2026-01-13
### Changed
- OMPE-77213: Updated docs

## [0.9.5] - 2025-12-15
### Changed
- Fixed tests using floats equals. Now using AlmostEqual

## [0.9.4] - 2025-12-15
### Changed
- OMPE-75214: fixed issue with writing properties to the camera

## [0.9.3] - 2025-12-11
### Changed
- Livestream message registration.

## [0.9.2] - 2025-12-10
### Changed
- Fixed action name as omni.kit.menu.utils menus using extension version number

## [0.9.1] - 2025-11-20
### Changed
- Updated documentation with AI agent.

## [0.9.0] - 2025-10-29
### Changes
- Created
