# USD Storage API Authentication

This extension enables USD Storage API authentication for Kit applications. It sits between the **Client Library** and **Web Portal**, using the streaming data channel to request and receive access tokens.

It uses portal-brokered OAuth2 via `omni.kit.livestream.messaging`. The extension receives tokens and registers servers through `omni.client` discovery. Discovered servers are also registered with the Content Browser via `connection_manager`.

Credentials are **never** stored or entered in Kit; they are obtained from the Web Portal over the livestream channel.

The auth callback **always accepts** storage auth requests, forwarding them to the portal. An `AuthStatusDialog` with a sliding activity indicator and Cancel button is shown during authentication, and a configurable timeout (`authCallbackTimeout`, default 60 s) triggers a modal error dialog if the portal does not respond. The portal may also push its configured timeout via the `refreshAccessToken.auth_timeout` field, which the extension picks up for subsequent auth flows. When the portal reports an auth failure (`authenticationError` event), Kit cancels the pending flow and shows the portal's `error_message` to the user.

Preconfigured discovery URLs are auto-mounted when a streaming client connects (via the `client_connected` livestream event). Each URL is authenticated sequentially using the same auth callback path as interactive auth. The user can cancel individual URLs without blocking the rest. Any URLs that fail are registered as placeholder entries in the Content Browser with an error status; the user can right-click and retry discovery.

## Quick start

```python
import omni.storage_api.auth as auth

ext = auth.get_instance()
handler = ext.get_auth_handler()

# Streaming/portal path: discover + register with portal auth
addresses = await ext.discover_and_register("https://discovery.example.com")

# Read preconfigured URLs from settings
urls = handler.get_preconfigured_urls()

# Auto-mount all preconfigured URLs
results = await handler.auto_mount_preconfigured()
```

## Documentation

- **[Overview](Overview.md)** -- Architecture, credential handling, end-to-end workflows, settings, and API summary.
- **[CHANGELOG](CHANGELOG.md)** -- Version history.
- **[python_api.md](../config/python_api.md)** -- Full Python API reference.
