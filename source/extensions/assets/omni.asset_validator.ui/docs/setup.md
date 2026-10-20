# Setup

```{eval-rst}
.. Caution::
   As of Kit 106.0.1, the extension is enabled by default with the
   `USD Composer app template <https://github.com/NVIDIA-Omniverse/kit-app-template/blob/main/templates/apps/usd_composer>`__.
   If you are creating your own application, for example based on the
   `kit base editor app template <https://github.com/NVIDIA-Omniverse/kit-app-template/tree/main/templates/apps/kit_base_editor>`__,
   the Asset Validator extension dependencies will need to be added in the ``.kit`` file.
   More information can be found in `Kit App Template <https://github.com/NVIDIA-Omniverse/kit-app-template>`__.
```

The extension can be enabled/disabled via the **Window -> Extensions** window if applicable, otherwise the
dependencies need to be added/removed from your Kit application `<my_app_name>.kit` file.

```{eval-rst}
.. code-block:: python

   [dependencies]
   "omni.asset_validator.core" = {}
   "omni.asset_validator.ui" = {}

.. Note:: Any changes to `.kit` files will require the application to be rebuilt for changes to take effect.
```

## Configuring Rules with Carbonite Settings

The *Asset Validator Window* is configurable at runtime using Carbonite settings. These *Asset Validator Window*
settings work with the ``omni.asset_validator.core`` settings to hide any rules in a Kit application.
```{eval-rst}
.. Note::
   Any rules hidden from the UI via these settings **will not be used during validation** runs initiated
   from the *Asset Validator Window* or the ``omni.asset_validator.ui`` Python API.
```

### Settings

- `hideDisabledCategories` can be used to exclude rules in the UI based on the
  `enabledCategories`/`disabledCategories` settings in `omni.asset_validator.core`.
- `hideDisabledRules` can be used to exclude rules in the UI based on the `enabledRules`/`disabledRules`
  settings in `omni.asset_validator.core`.
- `selectedCategories` can be used to select rules in the UI. While the above settings allow to show/hide
  rules/categories in the UI, this setting will default check them.
