```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

Scanning a collection trades throughput against how often the app gets to draw. These two settings
are where that trade is made: raising either finishes a scan sooner and makes the app less
responsive while it runs, lowering either does the opposite. The defaults were chosen against a
scan of a whole drive, where the worst frame gap fell from 9.10 s to 0.81 s and the median frame
rate rose from 7.9/s to 45.2/s, for about a third less directory throughput.

Both are read once per traverse. A missing, non-integer or non-positive value falls back to the
default rather than failing.

## Settings Provided by the Extension
### exts."omni.kit.browser.folder.core".traverse.max_concurrent_folders
- **Default Value**: 16
- **Description**: How many folders may be doing their own work - listing, classifying and resolving their files - at the same time, across the whole traverse. Each waits for an app frame before it starts, which is what lets Kit's asyncio pump go idle so the app can draw; the cap is what stops a deep tree having thousands of folders ready at once. Raise it for a faster scan and a less responsive app, lower it for the opposite.

### exts."omni.kit.browser.folder.core".traverse.yield_every_n_files
- **Default Value**: 32
- **Description**: How many files a folder may resolve before it hands a frame back to the app. Raise it to spend less time yielding on a collection of small files, lower it to keep the app drawing more often through a folder that is slow to resolve.

## Settings Used by the Extension but Provided by Another Extension
### /exts/omni.kit.browser.core/thumbnail_view/build_budget_ms
- **Description**: Milliseconds the detail view may spend building tiles before yielding a frame. A scan reports a change per folder it finds, so it is what bounds the cost of showing what a scan has produced. See the omni.kit.browser.core settings.
