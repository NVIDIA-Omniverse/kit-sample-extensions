# Quick Search [omni.kit.window.quicksearch]

QuickSearch can help you quickly find commands, materials, and other entities
in Omniverse Kit. Other extensions can register new models that are similar
to the TreeView models, new delegates that are similar to TreeView delegates,
and add their own content to QuickSearch.

# Requirements to the model

The model should be the same as the regular model for TreeView and based on
`ui.AbstractItemModel`.

The model should contain three columns:
 - 0 - Name
 - 1 - Description
 - 2 - Icon

If the model wants to execute the items when the user press ENTER, it should
contain the optional method `def execute(self, item)`.

# Requirements to the delegate

A delegate is the same as a regular delegate for TreeView.

When the model creates a delegate for flat list, it passes the keyword
argument `flat=True`.

