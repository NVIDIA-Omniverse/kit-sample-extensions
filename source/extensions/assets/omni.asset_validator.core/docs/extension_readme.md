# Omni Asset Validator (Core) [omni.asset_validator.core]

Validates assets against Omniverse specific rules to ensure they run smoothly across all Omniverse products.

###### Note
> Validates assets against Omniverse specific rules to ensure they run smoothly across all Omniverse products.


This uses the same validation API from [USD Validation NVIDIA](https://nvidia-omniverse.github.io/usd-validation-nvidia/) and its ``omni.asset_validator`` compatibility namespace, applied in the context of Omniverse. These symbols are imported into the new ``omni.asset_validator.core`` namespace. Use the appropriate extension or libraries depending on development needs.


It includes the following components:

- A **rule interface** and **registration mechanism** that can be called from external python modules.
- An **engine** that runs the rules on a given `Usd.Stage`, USD layer USD files, or recursively searches a folder for USD layers.
- An **issue fixing** interface for applying automated fixes if/when individual rules provide suggestions.


See [Asset Validator Docs](https://docs.omniverse.nvidia.com/kit/docs/asset-validator/latest/source/extensions/omni.asset_validator.core/docs/index.html) for more details.
