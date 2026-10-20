# NGSearch API extension

This extension exposes the powerful NGSearch API for easy use. Here is an example search:

```python
from omni.kit.ngsearch import async_search, StatusType
import asyncio

async def do_ngsearch():
    url = "omniverse://rc.ov.nvidia.com/Projects/DeepSearch/"
    query = "red rusty barrel"
    results = await async_search(query, url)

    if results.status == StatusType.OK:
        for result in results:
            ...


asyncio.ensure_future(do_ngsearch())
```
