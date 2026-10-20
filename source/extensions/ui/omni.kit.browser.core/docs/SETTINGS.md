```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.browser.core".thumbnail_view.build_budget_ms
- **Default Value**: 8
- **Description**: Milliseconds the detail view may spend creating tiles before it yields a frame. Tiles are built a few at a time because a browser attached to a running scan is asked to show thousands of new items between notifications, and creating them in one loop held the main thread for 100 seconds on a large scan. Raise it and tiles appear sooner at the cost of longer frames; lower it and the app stays smoother while the grid fills in more slowly. A missing, non-numeric or non-positive value falls back to the default.
