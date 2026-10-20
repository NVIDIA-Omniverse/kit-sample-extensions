# Node Registry Model
Now let's look at how we build the node list in the left panel of our example to show all the available nodes.

![](data/catalog.png)

First of all, we need a model to manage the node data and we use a tree-view model for that in the omni.kit.graph.editor.example. Our NodeRegistryModel is derived from the basic `ui.AbstractItemModel`.

Each tree leaf item is derived from `ui.AbstractItem` which is used to enacapsulate the data of the item which could contain the name, icon, url, etc. These data can be described by different value models inherited from `AbstractValueModel`.

There are a couple of important model APIs to define the tree model. `get_item_children` is the function to return the nodes at each level. For example, in the above image, the return value when input item is None will be [General, Miscellaneous], and the return value when input item is Miscellaneous is [Backdrop, Scene Graph, Input, Output].

`get_item_value_model` returns the value model which is the model that defines how each tree item is presenting its data. In the example, we only used the SimpleStringModel. But any model derived from `AbstractValueModel` will do, so you can define your own value model to describe a certain type of data.

## Node Filter
You probably noticed that there is a search field above the node lists, where you can search desired nodes with partial input. The results will be filtered to be the nodes matching the search input. This is done by controlling the visibility of the tree item in our example. If the item has name or information matching the input, the visibility is true otherwise false. The group visibility is controlled by each of the items inside. As long as one of the sub items is visible, the group visibility will be true.

## Quick Search Model
![](data/quicksearch.png)
In the example extension, when you press the Tab key on the canvas, you will see a pop up window of QuickSearch. This will show all the nodes which are registered with quick search in the extension, which is a quicker way to find the node you want if you have many extensions registered to the quick search.

It is trivial to implement QuickSearch. You will need to create a new model for that, NodeRegistryQuickSearchModel in our example. It could be very similar to the NodeRegistryModel discussed above. The only difference is `get_item_children` will return all the nodes available grouped by different registrations since we don't want the hierarchical look like the node registry panel.

To register with QuickSearch, we just need to import QuickSearchRegistry from omni.kit.window.quicksearch and register NodeRegistryQuickSearchModel with QuickSearchRegistry() using `register_quick_search_model`. You can create a tree delegate for the quick search. In the example, we just use the default GraphEditorCoreTreeDelegate from graph core.
