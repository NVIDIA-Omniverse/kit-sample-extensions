# Omniverse Services Client

Simple client library for Omniverse Services, allowing services to be called in a pythonic way and abstracts away the underlying transport.

## Usage example

For example, the following Python code corresponds to sending an HTTP request to http://localhost:8012/kit/status:

```python
import omni.services.client as _client

services = _client.AsyncClient("http://localhost:8012")
response = await services.kit.status()
```

To enable additional transports, search for `omni.services.transport` in the extension registry, or browse the list of available extensions in the Extension Manager.
