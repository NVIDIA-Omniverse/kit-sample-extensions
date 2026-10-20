# Omni Asset Validator (UI) [omni.asset_validator.ui]

Kit UIs for validating assets against Omniverse specific rules to ensure they run smoothly across Omniverse products.

It includes the following components:

- An Asset Validator Window to select rules and run validation on individual USD layer files, recursively search a folder for layer files and validate them all, or validate a live / in-memory `Usd.Stage`, such as the main stage in Kit based applications, for example the USD Composer app template.
- Content Browser context menus to launch the Asset Validator Window preset to the selected file/folder.
- Layer Window context menus to launch the Asset Validator Window preset to either the in-memory layer or the selected layer's file URI.
- Stage Window context menus to launch the Asset Validator Window preset to the currently open stage (i.e. the main stage of the application).

See [Asset Validator Docs](https://docs.omniverse.nvidia.com/kit/docs/asset-validator/latest/source/extensions/omni.asset_validator.ui/docs/index.html) for more details.
