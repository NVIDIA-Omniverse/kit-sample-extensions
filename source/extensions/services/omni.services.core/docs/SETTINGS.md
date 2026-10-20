```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension

### exts."omni.services.core".root_path
- **Default Value**: ""
- **Description**: The application URL root to use when the service is hosted behind a proxy.

### exts."omni.services.core".show_status_endpoint
- **Default Value**: true
- **Description**: Whether the shared service application exposes its status endpoint.

### exts."omni.services.core".strict_content_type
- **Default Value**: false
- **Description**: Whether JSON request bodies must include a JSON Content-Type header. Enable this after confirming all clients send an explicit JSON media type.

### exts."omni.services.core".health.activeProviders
- **Default Value**: ["omni.kit.app"]
- **Description**: The health providers that contribute to the `/livez`, `/readyz`, and `/startupz` endpoints.

### exts."omni.services.core".correlation_id.use_default_middleware
- **Default Value**: true
- **Description**: Whether to use the default correlation ID middleware provided by the Services framework.

### exts."omni.services.core".correlation_id.header_name
- **Default Value**: "X-Correlation-ID"
- **Description**: The HTTP request header used to read and propagate correlation IDs.

### exts."omni.services.core".correlation_id.update_request_header
- **Default Value**: true
- **Description**: Whether to update the incoming request header with the generated correlation ID.
