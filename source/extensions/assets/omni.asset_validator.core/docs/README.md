Omni Asset Validator (Core)
===========================

Validates assets against Omniverse-specific rules to ensure compatibility across all Omniverse products.

```{eval-rst}
.. note::
   This extension uses the same API as the ``omni.asset_validator`` open framework but includes additional
   rules and integrations for the Omniverse ecosystem. Symbols are re-exported into the
   ``omni.asset_validator.core`` namespace.
```

## Features

- Rule interface and registration mechanism for external Python modules
- Validation engine for `Usd.Stage`, USD layers, or recursive folder search
- Auto-fixing via `IssueFixer` when rules provide suggestions
- Additional Omniverse-specific validation rules
- Integration with Carbonite SDK and Omni USD Resolver
