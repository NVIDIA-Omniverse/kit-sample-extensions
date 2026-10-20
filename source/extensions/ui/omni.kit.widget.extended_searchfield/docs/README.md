# Extended Search Field

The extended search field replaces the search field in the content browser. It allows the user to select which search engine is active.

NGSearch makes use of the extended search field, which in turn relies on server support for "prefixes". The ability to use these search prefixes, and which of them are supported, depends on the type of servers and server-side plugins (such as DeepSearch. When prefixes are supported, the advanced search menu will be accessible, and the menu will only show the search options supported by the currently selected server.

When image search is available, the image icon will appear when hovering the mouse over the search bar. To search for an image, either drag and drop it onto the search field, select the path in the image menu, or right click on an image in the content browser and select 'Find Similar'. Files with thumbnails on an omniverse server are also supported.

Advanced search prefixes include `name`, `tag`, `created_by` and more (see below). In some cases, adding a `-` before a prefix can search for the opposite. For example `-ext:usd` will search for files that are not usd files. Currently negated prefixes aren't supported in the UI, and must be typed in manually. To modify a search, double click on the search bar.
