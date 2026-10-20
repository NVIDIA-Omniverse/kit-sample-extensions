# USD Storage API Authentication Extension

## Overview

The `omni.storage_api.auth` extension acts as an **intermediate layer** between the Client Library and Web Portal, enabling USD Storage API authentication on streaming Kit deployments (e.g. OV on DGXC). It communicates authentication events and messages through the streaming data channel using `omni.kit.livestream.messaging`.

### Key Purpose

1. **Token Refresh During Streaming**: USD Storage API uses stateless HTTP/gRPC requests that require access tokens with expiration dates. The extension enables token refreshing during active streaming sessions without interrupting the user experience.

2. **Server Registration**: The extension registers storage servers with the Client Library through portal-brokered discovery.

## Architecture

```text
+---------------+       Streaming Data Channel       +----------------+
|               | <--------------------------------> |                |
|  Web Portal   |                                    |  Kit Extension |
|               |  Token Refresh / Auth Messages     |                |
+---------------+                                    +-------+--------+
                                                             |
                                                             | omni.client API
                                                             v
                                                     +----------------+
                                                     |    Client      |
                                                     |    Library     |
                                                     +----------------+
                                                             |
                                                             v
                                                     +----------------+
                                                     | Content Browser|
                                                     | (connection_   |
                                                     |  manager)      |
                                                     +----------------+
```

### Auth Callback Behavior

The extension registers a **singleton auth callback** with `omni.client`. Whenever the Client Library needs a token for any storage server:

1. The callback **always returns `True`** (accepts the auth request) so the Client Library never falls through to other registered local auth callbacks — not even on reentrancy or unexpected exceptions.
2. The auth handle is stored and a pending future + timeout task are created.
3. An `addNewStorageUrl` message is dispatched to the Web Portal.
4. If the portal responds within `authCallbackTimeout` seconds, the token is applied via `omni.client.set_storage_access_token`.
5. On timeout, auth state is cleaned up and a modal timeout dialog is shown.

After any auth failure (portal error, timeout, cancel) the URL is added to an errored set. Subsequent invocations of the callback for the same URL (which `omni.client` generates every ~10 s while a failed auth handle persists) short-circuit with `True` and an empty-token release — no further `addNewStorageUrl` is dispatched. A fresh `discover_and_register` clears the mark so explicit retries re-engage the portal.

`omni.client` may invoke the callback on an internal worker thread (`Dummy-N`) where `asyncio` future creation would fail. The handler captures Kit's main event loop at init and marshals future/task creation + portal dispatch through `call_soon_threadsafe`.

### Progress Dialog

During callback-initiated auth, `AuthStatusDialog` shows a modal window with status text, a sliding indicator, and a Cancel button. Cancelling (either the Cancel button or the window X) invokes `_cleanup_callback_auth` and marks the Content Browser entry as ERROR.

### Discovery Removal

When a discovery server is removed via connection_manager, the extension subscribes to `DISCOVERY_SERVER_REMOVED_EVENT` and clears its `_request_handles` and auth state for that URL. This way, re-adding the same URL interactively goes through the normal new-URL auth path.

### Client-Connected Mount Flow (Preconfigured URLs)

When `preconfiguredDiscoveryUrls` is configured, the extension defers mounting until a streaming client connects:

1. **Startup** -- The extension subscribes to the `omni.kit.livestream.client_connected:immediate` event but does **not** start any polling or mounting. The auth callback is registered immediately so on-demand auth still works.
2. **Client connects** -- When a streaming client connects via the web portal, the `client_connected` event fires. The extension calls `discover_and_register` for each preconfigured URL **sequentially**. The auth callback handles the token exchange with the portal -- the same code path as interactive auth.
3. **Cancel support** -- If the user clicks Cancel on the auth dialog, only the **current** URL is skipped; the remaining URLs continue mounting.
4. **Failure fallback** -- Any URLs that fail (timeout or error) are registered as **placeholder** entries in the Content Browser with an error status ("Web portal not connected"). The user can right-click a placeholder and choose **Retry Discovery**.

Already-registered URLs are skipped in both the auth callback and `auto_mount_preconfigured`.

### Content Browser Integration

After successful discovery, the extension registers servers with the Content Browser via `omni.kit.widget.connection_manager`:

```python
mgr.registry.add_discovery_server(
    name=discovery_url,
    discovery_url=discovery_url,
    cached_addresses=list(addresses),
)
```

The extension also transfers its `omni.client` registration handle to the connection_manager's internal entry, preventing redundant re-discovery when the user clicks a node. The `DISCOVERY_SERVER_ADDED_EVENT` fired by `add_discovery_server` triggers the Content Browser to auto-expand and show the new discovery items.

If `connection_manager` is not available (e.g. headless Kit), servers are still registered with `omni.client` and usable programmatically.

## How the Extension Accesses and Handles Credentials

### Where credentials come from

- Access tokens are obtained from the **Web Portal** via the streaming data channel. The portal performs the OAuth2 flow. Kit has no direct access to user passwords or refresh tokens.

### How the extension receives credentials (streaming)

- Credentials reach the extension via the `refreshAccessToken` event from `omni.kit.livestream.messaging`.
- The event payload includes:
  - **`access_token`** (required): the OAuth2 access token.
  - **`discovery_url`** (optional): the discovery URL this token applies to, or `"*"` for a wildcard refresh.

### How the extension handles credentials

- **No long-term storage**: The extension does **not** persist access tokens to settings or to disk.
- **Immediate handoff**: On receipt of a valid token, the extension calls `omni.client.set_storage_access_token(auth_handle, access_token)`. The Client Library handles subsequent requests.

## End-to-End Workflows

### Workflow 1: Programmatic Discovery Registration (Streaming)

Register a discovery URL with portal-brokered authentication.

1. Caller invokes `ext.discover_and_register(discovery_url)`.
2. Extension registers an auth handler for the discovery URL.
3. Extension calls `omni.client.register_storage_from_discovery_with_callback`, which triggers the auth callback.
4. Auth callback sends `addNewStorageUrl` to the Web Portal.
5. Portal runs OAuth2, obtains token, sends `refreshAccessToken` to Kit.
6. Extension receives the token, calls `omni.client.set_storage_access_token`.
7. Discovery completes, returning a list of server addresses.
8. Servers are registered with `omni.client` and accessible.

### Workflow 2: Preconfigured Auto-Mount (Client Connected)

Discovery URLs configured in settings are mounted automatically when a streaming client connects.

1. **Configuration** -- `preconfiguredDiscoveryUrls` is set in `.kit` or settings.
2. **Startup** -- Extension subscribes to the `client_connected` livestream event. No polling or mounting occurs yet.
3. **Client connects** -- A streaming client connects via the web portal, firing the `client_connected` event.
4. **Auto-mount** -- Extension runs `discover_and_register` for each preconfigured URL sequentially. The auth callback sends `addNewStorageUrl` to the portal and waits for a token -- the same path as interactive auth. Already-registered URLs are skipped.
5. **Content Browser** -- Successfully discovered servers are registered with `connection_manager.registry.add_discovery_server`.
6. **Cancel / Failure** -- The user can click Cancel to skip the current URL. Any URLs that fail are added as placeholder entries with error status.
7. **Result** -- Servers are registered with `omni.client` and visible in the Content Browser.

**Configuration** example:
```toml
[settings.exts."omni.storage_api.auth"]
preconfiguredDiscoveryUrls = ["https://discovery.example.com"]
authCallbackTimeout = 60     # Per-URL timeout for portal auth response (seconds)
```

### Workflow 3: Callback-Initiated Authentication

When the Client Library triggers auth on its own (e.g. when encountering a storage URL from another extension):

1. **Auth callback fires** -- The singleton callback accepts, stores the auth handle, and sends `addNewStorageUrl` to the portal.
2. **Progress dialog** -- An `AuthStatusDialog` with a sliding activity indicator and a Cancel button is shown.
3. **Portal responds** -- Token is set via `set_storage_access_token`; dialog is dismissed.
4. **Cancel** -- If the user clicks Cancel, the current auth is skipped immediately.
5. **Timeout** -- If the portal does not respond within `authCallbackTimeout` seconds, auth state is cleaned up and a modal timeout dialog is shown.

### Workflow 4: Token Refresh (During Session)

1. **Trigger** -- Either:
   - **Proactive**: Portal refreshes the token and sends `refreshAccessToken` (optionally with discovery URL `"*"` for all handles).
   - **Reactive**: Client Library invokes the auth callback on 401; extension sends `requestTokenRefresh` to the portal.
2. **Portal** returns a new access token.
3. **Extension** calls `omni.client.set_storage_access_token(handle, token)`.
4. **Result** -- Client Library uses the new token for subsequent requests.

## Quick Start

```python
import omni.storage_api.auth as auth

ext = auth.get_instance()
handler = ext.get_auth_handler()

# Streaming/portal path: discover + register with portal auth
addresses = await ext.discover_and_register("https://discovery.example.com")

# Read preconfigured URLs from settings
urls = handler.get_preconfigured_urls()

# Auto-mount all preconfigured URLs (usually done automatically on startup)
results = await handler.auto_mount_preconfigured()

# Manual testing helpers
handler.manual_token_refresh("https://discovery.example.com")
handler.manual_new_storage_url("https://discovery.example.com")
```

## Messaging Events

Communication with the Web Portal uses these event types via `omni.kit.livestream.messaging`:

| Event | Direction | Description |
|---|---|---|
| `requestTokenRefresh` | Kit -> Portal | Request a new access token for a discovery URL |
| `addNewStorageUrl` | Kit -> Portal | Request authentication for a new discovery URL |
| `refreshAccessToken` | Portal -> Kit | Deliver a new/refreshed access token |
| `authenticationError` | Portal -> Kit | Report an auth failure (e.g. user rejected sign-in, IdP error) |

All events carry a `discovery_url` field in their payload.

`refreshAccessToken` additionally carries:
- `access_token` (required) -- the new token; `discovery_url = "*"` applies to all registered handles.
- `auth_timeout` (optional, seconds) -- the portal's configured timeout. When present, Kit stores it and uses it for **subsequent** auth flows; the in-flight transaction is unaffected. Kit's timeout should be `>=` the portal's so the user sees the portal's specific error before Kit's generic timeout fires.

`authenticationError` payload: `{discovery_url, error_code, error_message}`. Kit cancels the matching pending auth and discovery futures, pushes an empty token to the stored `omni.client` auth handle (so any in-flight `stat`/`list` ops release the `Core` rwlock as readers instead of waiting forever), drops all state for the URL, and shows a modal with the portal's `error_message`. The rwlock release is what prevents a deadlock the next time the Content Browser's right-click menu invokes `omniClientStop` on the UI thread. A late error arriving after the user has already cancelled the dialog is dropped so no stale popup is shown.

## Settings

| Setting | Type | Default | Description |
|---|---|---|---|
| `preconfiguredDiscoveryUrls` | `list[str]` | `[]` | Discovery URLs to auto-mount when a streaming client connects |
| `authCallbackTimeout` | `float` | `60` | Per-URL timeout for portal auth response (seconds); a timeout dialog is shown on expiry. Overridden at runtime by the portal-supplied `auth_timeout` if any `refreshAccessToken` has delivered one. |

## Additional Resources

- **python_api.md** -- Detailed Python API reference
