# Usage Examples

## Create Basic Browser Widget with Simple Model

```python
import omni.ui as ui
from omni.kit.browser.core import AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem, BrowserWidget

# Create a simple browser model
class SimpleBrowserModel(AbstractBrowserModel):
    def __init__(self):
        super().__init__()

    def get_collection_items(self):
        return [
            CollectionItem("Assets", "file://assets"),
            CollectionItem("Materials", "file://materials")
        ]

    def get_category_items(self, item):
        if item.name == "Assets":
            return [
                CategoryItem("Models", count=5),
                CategoryItem("Textures", count=10)
            ]
        return [CategoryItem("PBR Materials", count=8)]

    def get_detail_items(self, item):
        details = []
        for i in range(item.count):
            details.append(DetailItem(
                f"{item.name} Item {i+1}",
                f"file://{item.name.lower()}/item_{i+1}",
                f"thumbnail_{i+1}.jpg"
            ))
        return details

    def get_sort_args(self):
        return {"key": lambda x: x.name, "reverse": False}

# Create window and browser widget
window = ui.Window("Browser Example", width=800, height=600)
with window.frame:
    model = SimpleBrowserModel()
    browser_widget = BrowserWidget(model)

# Set the collection index to the first collection item
browser_widget.collection_index = 0
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.browser.core/data/docs_images/usage_preview.png
---
align: center
---
```

---

## Create Browser with Search Bar and Options Menu

```python
import omni.ui as ui
from omni.kit.browser.core import BrowserSearchBar, OptionsMenu, OptionMenuDescription, BrowserWidget, AbstractBrowserModel

# Create a simple model (same as above)
class SimpleBrowserModel(AbstractBrowserModel):
    def get_collection_items(self):
        return [CollectionItem("Library", "file://library")]

    def get_category_items(self, item):
        return [CategoryItem("Documents", count=3)]

    def get_detail_items(self, item):
        return [DetailItem("Document 1", "file://doc1", "doc1.jpg")]

    def get_sort_args(self):
        return None

# Create options menu with custom items
options_menu = OptionsMenu()
options_menu.append_menu_item(OptionMenuDescription(
    "Custom Action",
    clicked_fn=lambda: print("Custom action clicked!")
))
options_menu.append_menu_item(OptionMenuDescription(""))  # Separator

# Create window with search bar and browser
window = ui.Window("Browser with Search", width=800, height=600)
with window.frame:
    with ui.VStack(spacing=4):
        BrowserSearchBar(
            enable_navigation_visibility=True,
            options_menu=options_menu
        )
        model = SimpleBrowserModel()
        browser_widget = BrowserWidget(model)

# Bind the search bar to browser widget
search_bar.bind_browser_widget(browser_widget)

# Set the collection index to the first collection item
browser_widget.collection_index = 0
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.browser.core/data/docs_images/create_browser_with_search_bar_and_options_menu.png
---
align: center
---
```

---

## Create Custom Detail Delegate with Tooltips

```python
import omni.ui as ui
from omni.kit.browser.core import DetailDelegate, BrowserWidget, AbstractBrowserModel, DetailItem

# Create custom detail delegate
class CustomDetailDelegate(DetailDelegate):
    def get_tooltip(self, item):
        return f"Name: {item.name}\nURL: {item.url}"

    def get_label(self, item):
        return item.name.upper()  # Show labels in uppercase

    def on_click(self, item):
        print(f"Clicked on: {item.name}")

    def on_double_click(self, item):
        print(f"Double-clicked on: {item.name}")
        super().on_double_click(item)  # Execute default action

# Simple model for demonstration
class SimpleBrowserModel(AbstractBrowserModel):
    def get_collection_items(self):
        return [CollectionItem("Items", "file://items")]

    def get_category_items(self, item):
        return [CategoryItem("Category A", count=2)]

    def get_detail_items(self, item):
        return [
            DetailItem("Item One", "file://item1", "thumb1.jpg"),
            DetailItem("Item Two", "file://item2", "thumb2.jpg")
        ]

    def get_sort_args(self):
        return None

# Create window with custom delegate
window = ui.Window("Custom Delegate Browser", width=800, height=600)
with window.frame:
    model = SimpleBrowserModel()
    custom_delegate = CustomDetailDelegate(model)
    browser_widget = BrowserWidget(
        model,
        detail_delegate=custom_delegate,
        detail_thumbnail_size=64
    )

# Set the collection index to the first collection item
browser_widget.collection_index = 0
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.browser.core/data/docs_images/create_custom_detail_delegate_with_tooltips.png
---
align: center
---
```

---

## Create Tree Browser Widget

```python
import omni.ui as ui
from omni.kit.browser.core import TreeBrowserWidget, TreeCategoryDelegate, AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem

# Create model with hierarchical categories
class TreeBrowserModel(AbstractBrowserModel):
    def get_collection_items(self):
        return [CollectionItem("Project Files", "file://project")]

    def get_category_items(self, item):
        # Create category with children
        parent_category = CategoryItem("Root", count=5)
        child1 = CategoryItem("Sub 1", count=3, parent=parent_category)
        child2 = CategoryItem("Sub 2", count=2, parent=parent_category)
        parent_category.children = [child1, child2]

        # Create an empty category
        empty_category = CategoryItem("Empty", count=0)

        return [parent_category, empty_category]

    def get_detail_items(self, item):
        details = []
        for i in range(item.count):
            details.append(DetailItem(
                f"File {i+1} in {item.name}",
                f"file://{item.name}/file_{i+1}",
                f"file_icon_{i+1}.png"
            ))
        return details

    def get_sort_args(self):
        return {"key": lambda x: x.name}

# Create tree browser widget
window = ui.Window("Tree Browser", width=800, height=600)
with window.frame:
    model = TreeBrowserModel()
    tree_delegate = TreeCategoryDelegate(hide_zero_count=True)
    tree_browser = TreeBrowserWidget(
        model,
        category_delegate=tree_delegate,
        category_tree_mode=True
    )

# Set the collection index to the first collection item
tree_browser.collection_index = 0
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.browser.core/data/docs_images/create_tree_browser_widget.png
---
align: center
---
```
