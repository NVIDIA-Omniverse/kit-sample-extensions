```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.browser.material".data.timeout
- **Default Value**: 5
- **Description**: Configures the timeout (in seconds) for fetching material data, used during the initialization of the MaterialBrowserModel.

### exts."omni.kit.browser.material".enabled
- **Default Value**: True
- **Description**: Determines whether the Material Browser extension is active, controlling UI display and the registration of associated actions.

### exts."omni.kit.browser.material".load_after_startup
- **Default Value**: False
- **Description**: Indicates if the Material Browser window should immediately build its UI on startup or defer UI construction until its frame is built.

### exts."omni.kit.browser.material".doNotCastShadows.exception_files
- **Default Value**: ['Mirror.mdl']
- **Description**: Provides a list of file names for which the "do not cast shadows" feature will be skipped when applying material properties.

### exts."omni.kit.browser.material".doNotCastShadows.folders
- **Default Value**: []
- **Description**: Specifies folder names where materials are automatically set to not cast shadows, unless overridden by exception files.

### exts."omni.kit.browser.material".max_thumbnail_size
- **Default Value**: 512
- **Description**: Defines the maximum size (width or height) allowed for material thumbnails in the Material Browser window.

### exts."omni.kit.browser.material".min_thumbnail_size
- **Default Value**: 32
- **Description**: Sets the minimum size (width or height) for material thumbnails in the Material Browser window.

### exts."omni.kit.browser.material".folders_hide_in_category
- **Default Value**: ['2023_1']
- **Description**: Lists folder category identifiers that should be hidden in the material browser's category view.

### exts."omni.kit.browser.material".folders
- **Default Value**: ['https://omniverse-content-production.s3.us-west-2.amazonaws.com/Materials/2023_1']
- **Description**: Specifies the material folder URLs from which the browser will load material assets.

### exts."omni.kit.browser.material".usd_reader.threaded
- **Default Value**: True
- **Description**: Opens USD files on a worker thread instead of the event loop, so the app keeps drawing through a file that is slow to open. A large file is slow however few of them there are: scanning a library holding one 10,000 prim file, the main thread was inside the reader in 0 of 50 samples with this on, and in almost all of them with it off, where the app stops responding for as long as that one open takes. False reads on the loop, which costs the app those frames and buys nothing back: scanning a 2,649 material library took 8.4 s threaded against 8.7 s on the loop from local disk, and 14.3 s against 14.2 s from S3 - the same within the spread - while the app ran at 96 fps threaded and 25 fps on the loop. The worker touches USD only when there is a file to read: doing it at startup initialises USD before the extensions that register schemas have finished.

### exts."omni.kit.browser.material".usd_reader.skip_foreign_arcs
- **Default Value**: True
- **Description**: Leaves uncomposed any arc - payload, reference, sublayer or clip - whose target is in a different storage location than the file being read: another server, or remote against local. Same-location arcs still compose, and a relative path is always the same location as the file that refers to it, so this does not stop a file reaching another folder on the same disk or the same host. When a reference, sublayer or clip is left uncomposed the materials are read from the file's own layer instead, so any material that arrives only through that arc is not listed. False composes everything, which stalls a scan for minutes on an arc naming an unreachable host.

## Settings Used by the Extension but Provided by Another Extension
### /app/warmupMode
- **Description**: Indicates whether the application is running in warmup mode, triggering early initialization of the Material BrowserModel.
