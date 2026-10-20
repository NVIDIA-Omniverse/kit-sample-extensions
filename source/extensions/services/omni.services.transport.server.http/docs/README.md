# Kit services http(s) server transport

When enabled, provides an http and/or https server.
The servers will mount the omni.services.core.main app and will serve it up over http.


## HTTP

To enable/disable the HTTP server set the following setting to `true` or `false`. (Default: `true`):
`exts."omni.services.transport.server.http".http.enabled`

The port can be specified with the following setting:
`exts."omni.services.transport.server.http".port`


## HTTPS

To enable/disable the HTTPS server set the following setting to `true` or `false`. (Default: `false`):
`exts."omni.services.transport.server.http".https.enabled`

When enabling the HTTPS server, users are also expected to configure the SSL configuration.
The following settings are available:
  - `exts."omni.services.transport.server.http".ssl.ssl_keyfile`
  - `exts."omni.services.transport.server.http".ssl.ssl_certfile`
  - `exts."omni.services.transport.server.http".ssl.ssl_version`
  - `exts."omni.services.transport.server.http".ssl.ssl_cert_reqs`
  - `exts."omni.services.transport.server.http".ssl.ssl_ca_certs`
  - `exts."omni.services.transport.server.http".ssl.ssl_ciphers`

The following SSL settings are mandatory when Enabling HTTPS
 - `exts."omni.services.transport.server.http".ssl.ssl_keyfile`
 - `exts."omni.services.transport.server.http".ssl.ssl_certfile`


The port can be specified with the following setting:
`exts."omni.services.transport.server.http".https.port`

## CORS

To enable/disable CORS set the following setting to `true` or `false`. (Default: `false`):
`exts."omni.services.transport.server.http".cors.enabled`

When enabled the following settings can be configured:
`exts."omni.services.transport.server.http".cors.allow_origins` (Default: `[]`)
`exts."omni.services.transport.server.http".cors.allow_credentials` (Default: `false`)
`exts."omni.services.transport.server.http".cors.allow_methods` (Default: `[]`)
`exts."omni.services.transport.server.http".cors.allow_headers` (Default: `[]`)
