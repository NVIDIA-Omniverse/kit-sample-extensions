# Omniverse Services HTTP Client Transport

The HTTP consumer, when paired with `omni.services.client` allows users to make requests to Omniverse micro services via HTTP.

## Usage example

After enabling this extension, include similar code in your extension:

```python
from omni.services.client import async_client

# [...]

client = async_client("http://<url>")
```

Or, if using HTTPs:

```python
client = async_client("https://<url>")
```

To use custom SSL files or use self-signed certificates, configure the following extension settings:

```toml
exts."omni.services.transport.client.https_async".cacert_file = "<path to .crt file>"
exts."omni.services.transport.client.https_async".ssl_key_file = "<path to .key file>"
exts."omni.services.transport.client.https_async".ssl_pem_file = "<path to .pem file>"
```
