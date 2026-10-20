```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The **omni.kit.browser.core** extension provides a set of core APIs to support browser functionality within Omniverse Kit SDK. It defines a data model and UI components that manage hierarchical content through collections, categories, and details. The extension is focused on enabling developers to customize how browser items are retrieved, displayed, and interacted with through a series of abstract models, delegates, and widgets.

<div align="center">

```{mermaid}
graph TD
    %% Inheritance relationships
    TreeCategoryDelegate --> CategoryDelegate
    TreeBrowserWidget --> BrowserWidget

    %% Model-Item relationships
    AbstractBrowserModel -.->|contains| CategoryItem
    AbstractBrowserModel -.->|contains| CollectionItem
    AbstractBrowserModel -.->|contains| DetailItem

    %% Delegate-Model relationships
    CategoryDelegate -.->|represents| AbstractBrowserModel
    DetailDelegate -.->|represents| AbstractBrowserModel

    %% Widget-Model relationships
    BrowserWidget -.->|uses| AbstractBrowserModel

    %% Delegate-Widget relationships
    CategoryDelegate -.->|renders| BrowserWidget
    DetailDelegate -.->|renders| BrowserWidget
    TreeCategoryDelegate -.->|renders| TreeBrowserWidget
```

</div>

```{image} ../../../../source/extensions/ui/omni.kit.browser.core/data/preview.png
---
align: center
---
```


## Concepts

- The extension introduces an [AbstractBrowserModel](omni.kit.browser.core/omni.kit.browser.core.AbstractBrowserModel) that requires implementations for obtaining collection, category, and detail items.
- It encapsulates browser items through models such as [CategoryItem](omni.kit.browser.core/omni.kit.browser.core.CategoryItem), [CollectionItem](omni.kit.browser.core/omni.kit.browser.core.CollectionItem), and [DetailItem](omni.kit.browser.core/omni.kit.browser.core.DetailItem), ensuring consistent data handling and filtering.
- UI components like [BrowserWidget](omni.kit.browser.core/omni.kit.browser.core.BrowserWidget), [TreeBrowserWidget](omni.kit.browser.core/omni.kit.browser.core.TreeBrowserWidget), and [BrowserSearchBar](omni.kit.browser.core/omni.kit.browser.core.BrowserSearchBar) centralize user interactions, while specialized delegates ([CategoryDelegate](omni.kit.browser.core/omni.kit.browser.core.CategoryDelegate), [DetailDelegate](omni.kit.browser.core/omni.kit.browser.core.DetailDelegate), [TreeCategoryDelegate](omni.kit.browser.core/omni.kit.browser.core.TreeCategoryDelegate)) control the visual presentation.

## Functionality

- **Data Management:** By implementing the abstract methods of [AbstractBrowserModel](omni.kit.browser.core/omni.kit.browser.core.AbstractBrowserModel), users can define how collections, categories, and details are loaded and cached.
- **User Interface:** The provided widgets combine lists, tree views, and search bars into a cohesive browsing experience for navigating hierarchical data.
- **Interactivity:** The [OptionsMenu](omni.kit.browser.core/omni.kit.browser.core.OptionsMenu) and its associated [OptionMenuDescription](omni.kit.browser.core/omni.kit.browser.core.OptionMenuDescription) allow customization of actions within the browser UI, while the [create_drop_helper](omni.kit.browser.core/omni.kit.browser.core.create_drop_helper) utility function facilitates the integration of drag and drop functionality, optionally leveraging viewport interfaces when available.

## Key Components

- **Data Models:**
  - [AbstractBrowserModel](omni.kit.browser.core/omni.kit.browser.core.AbstractBrowserModel)
  - [CategoryItem](omni.kit.browser.core/omni.kit.browser.core.CategoryItem), [CollectionItem](omni.kit.browser.core/omni.kit.browser.core.CollectionItem), [DetailItem](omni.kit.browser.core/omni.kit.browser.core.DetailItem)

- **UI Widgets:**
  - [BrowserSearchBar](omni.kit.browser.core/omni.kit.browser.core.BrowserSearchBar), [BrowserWidget](omni.kit.browser.core/omni.kit.browser.core.BrowserWidget), [TreeBrowserWidget](omni.kit.browser.core/omni.kit.browser.core.TreeBrowserWidget)

- **Delegates:**
  - [CategoryDelegate](omni.kit.browser.core/omni.kit.browser.core.CategoryDelegate), [DetailDelegate](omni.kit.browser.core/omni.kit.browser.core.DetailDelegate), [TreeCategoryDelegate](omni.kit.browser.core/omni.kit.browser.core.TreeCategoryDelegate)

- **Options Menu:**
  - [OptionsMenu](omni.kit.browser.core/omni.kit.browser.core.OptionsMenu), [OptionMenuDescription](omni.kit.browser.core/omni.kit.browser.core.OptionMenuDescription)

- **Utility:**
  - [create_drop_helper](omni.kit.browser.core/omni.kit.browser.core.create_drop_helper) (supports drag and drop by optionally integrating with viewport window functionalities)

By providing these well-defined APIs and interfaces, **omni.kit.browser.core** lays the foundation for building and customizing browser-based views within the Omniverse Kit SDK.
