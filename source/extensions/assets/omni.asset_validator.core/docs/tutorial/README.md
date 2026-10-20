Introduction
============

Currently, there are two main components:
- [Omni Asset Validator (Core)](../index.rst): Core components for Validation engine. Feel free to use this component to
implement programmatic functionality or extend Core functionality through its framework.
- [Omni Asset Validator (UI)](../../../omni.asset_validator.ui/docs/index.rst): Convenient UI for Omniverse.
For use in Omniverse Kit applications.

The following tutorial will help you to:
- Run basic operations for Asset Validator, `ValidationEngine` and `IssueFixer`.
- Get familiar with existing Rules to diagnose and fix problems.
- Create your custom Rules.

Tutorials
=========

Enabling The Asset Validator Extension
--------------------------------------
 ```{eval-rst}
.. Caution:: As of kit 106.0.1, these extensions are enabled by default within the USD Composer app template in the `sample app templates <https://github.com/NVIDIA-Omniverse/kit-app-template/blob/main/templates/apps/usd_composer>`__. If you are creating your own application, for example based on the `kit base editor app template <https://github.com/NVIDIA-Omniverse/kit-app-template/tree/main/templates/apps/kit_base_editor>`__, the Asset Validator will need to be added as a dependency to the application's ``.kit`` file. More information can be found here: `Kit App Template <https://github.com/NVIDIA-Omniverse/kit-app-template>`__.
```
The extension can be enabled/disabled via the **Window -> Extensions** window if applicable, otherwise the dependencies need to be added/removed from your Kit application `<my_app_name>.kit` file.
```{eval-rst}
.. code-block:: python

   [dependencies]
   "omni.asset_validator.core" = {}
   "omni.asset_validator.ui" = {}

.. Note:: Any changes to `.kit` files will need the application to be rebuilt for changes to take effect.
```

## Testing Assets

In order to run Asset Validator, we need to enable the extension `Omni asset validator (Core)`. Optionally we can also
enable `Omni asset validator (UI)` to perform similar operations using the user interface. Through this tutorial we will
use `Script Editor`, enable it under the `Window` menu.

To run a simple asset validation, with `Script Editor` execute the following code.

```{eval-rst}
.. literalinclude:: snippets/simple_validation.py
   :language: python
   :linenos:
```

```{eval-rst}
.. note::
  For more information about ValidationEngine together with more examples can be found at the `ValidationEngine API <../api.html#omni.asset_validator.core.ValidationEngine>`_.
```

The above code would produce similar results to.

```{eval-rst}
.. literalinclude:: snippets/simple_validation.out
   :language: none
   :linenos:
```

The main result of validation engine is called an `Issue`. The main task of Asset validation is to detect and fix issues.
An `Issue` has important information on how to achieve both tasks.
- *Detect*. Once an issue has been found it offers a description of the problem (through a human-readable message), its
severity, the `Rule` that found the issue and its location (i.e. the `Usd.Prim`).
- *Fix*. If a suggestion is available, it will help to address the `Issue` found. Information on the `Rule` and the location
of the issue will be used to address it.

In the following section we will walk you through on how to identify and fix issues.

```{eval-rst}
.. note::
  For more information see the `Issue API <../api.html#omni.asset_validator.core.Issue>`_.
```

## Understanding Rules

`Omni asset validator (Core)` ships with multiple rules, in the previous example we already covered two:
- `StageMetadataChecker`: All stages should declare their `upAxis` and `metersPerUnit`.
Stages that can be consumed as referencable assets should furthermore have
a valid `defaultPrim` declared, and stages meant for consumer-level packaging
should always have upAxis set to `Y`.
- `OmniDefaultPrimChecker`: Omniverse requires a single, active, `Xformable` root prim,
also set to the layer's defaultPrim.

Refer to [Rules](../rules.rst) for the rest of rules. In the previous example when calling `ValidationEngine` we invoked
all rules available. `ValidationRulesRegistry` has a registry of all rules to be used by `ValidationEngine`.

```{eval-rst}
.. literalinclude:: snippets/print_rules.py
   :language: python
   :linenos:
```

If we want to have finer control of what we can execute, we can also specify which rules to run, for example:

```{eval-rst}
.. literalinclude:: snippets/rule_validation.py
   :language: python
   :linenos:
   :emphasize-lines: 4
```
There are two new elements present here:
- `initRules`: By default set to `true`. if set to `false`, no rules will be automatically loaded.
- `enableRule`: A method of `ValidationEngine` to add rules.

The above would produce the following result:

```{eval-rst}
.. literalinclude:: snippets/rule_validation.out
   :language: none
   :linenos:
```

In this particular case, `OmniDefaultPrimChecker` has implemented a suggestion for this specific issue. The second important class in `Core`
we want to cover is `IssueFixer`, the way to invoke it is quite straightforward.

```{eval-rst}
.. literalinclude:: snippets/simple_fix.py
   :language: python
   :linenos:
```
`fixer.fix` will receive the list of issues that should be addressed. The list of issues to address can be accessed through `issues` method in `Results` class.

```{eval-rst}
.. note::
  For more information about IssueFixer see `IssueFixer API <../api.html#omni.asset_validator.core.IssueFixer>`_.
```

By combining the previous two examples we can now, detect and fix issues for a specific rule.

```{eval-rst}
.. literalinclude:: snippets/rule_fixing.py
   :language: python
   :linenos:
```

We can find the issue reported by `OmniDefaultPrimChecker` is fixed:
```{eval-rst}
.. literalinclude:: snippets/rule_fixing.out
   :language: none
   :linenos:
```

```{eval-rst}
.. note::
  Try to repeat the same steps using the `UI <../../../omni.asset_validator.ui/docs/index.html>`_.
```

## Custom Rule: Detection

If the shipped rules are not enough for your needs you can also implement your own rule.
`ValidationEngine` allows to be extensible, by levering users to add its own rules.
To add a new rule extend from `BaseRuleChecker`. The most simple code to achieve this is as follows:

```{eval-rst}
.. literalinclude:: snippets/custom_rule_empty.py
   :language: python
   :linenos:
   :emphasize-lines: 4
```

We can see our method `CheckPrim` being invoked for every Prim. However, our output is empty because `CheckPrim` has not notified of any issues.

```{eval-rst}
.. literalinclude:: snippets/custom_rule_empty.out
   :language: none
   :linenos:
```

```{eval-rst}
.. note::
  `CheckPrim` is not the only method available, see more at `BaseRuleChecker API <../api.html#omni.asset_validator.core.BaseRuleChecker>`_.
```

To add a bit of logic we can change our class to report a single failure when we encounter the prim whose path is `/Hello/World`:
```{eval-rst}
.. literalinclude:: snippets/custom_rule_full.py
   :language: python
   :linenos:
   :emphasize-lines: 7,8,9,10
```
There are three levels of issues:
- *Errors*: Errors are used to notify user that something unexpected happened that would not let the `Rule` run (i.e. File not found error). Added through the method `_AddError`.
- *Warnings*: Warnings are used to notify users that though correct data is found it could cause a potential problem. Added through the method `_AddWarning`.
- *Failures*: The most common way to report an `Issue` in Asset Validation. This can be done through `_AddFailedCheck` as seen in the example above.
- *Infos*: Information that is reported by the rules to notify users something is important and not an error nor a potential problem. Also,
it doesn't need to be fixed. It can be added through the method `_AddInfo`.

Above code will generate:

```{eval-rst}
.. literalinclude:: snippets/custom_rule_full.out
   :language: none
   :linenos:
```

With our `Rule` implemented the next step is to propose a suggestion to fix it.

## Custom Rule: Fix

The fixing interface requires to implement a `Suggestion`. A `Suggestion` will take as parameters:
- *Stage*: The original stage where the issue was found.
- *Location*: The location defined in the Issue (i.e. the `at` attribute). This will help us to scope down our fix.

```{eval-rst}
.. literalinclude:: snippets/custom_rule_validate.py
   :language: python
   :linenos:
```

It will now produce the following output.

```{eval-rst}
.. literalinclude:: snippets/custom_rule_validate.out
   :language: python
   :linenos:
```

As we can see we have now a suggestion with a description and a method to invoke. The full example will be:

```{eval-rst}
.. literalinclude:: snippets/custom_rule_fix.py
   :language: python
   :linenos:
   :emphasize-lines: 14,15,16,17
```

Notice how the `NotImplementedError` error was not thrown during `fixer.fix`. However, we can access the result of
execution by inspecting `result`:
```{eval-rst}
.. literalinclude:: snippets/custom_rule_fix.out
   :language: python
   :linenos:
```

Finally, if you decide to run your custom `Rule` with the rest of the rules, it may be useful to register it in
`ValidationRulesRegistry`, this can be done using `registerRule`.

```{eval-rst}
.. literalinclude:: snippets/custom_rule_register.py
   :language: python
   :linenos:
```

```{eval-rst}
.. literalinclude:: snippets/custom_rule_register.out
   :language: none
   :linenos:
```

## Custom Rule: Locations

What we are doing is adding an opinion to the prim "/Hello/World". In the previous section we learned how to create a ``Rule`` and issue a ``Failure``.
The data model is similar to the following code snippet:

```{eval-rst}
.. literalinclude:: snippets/fix_at_all.py
   :language: python
   :linenos:
```

The output of the above snippet should show *first* the root layer (i.e. ``tutorial.usda``) and second the sublayer (i.e. ``layer.usda``).
While this may be correct for above issue, different issues may need to override this information.

```{eval-rst}
.. literalinclude:: snippets/fix_at_all.out
   :language: none
   :linenos:
```

Every issue, has associated fixing sites (i.e. property ``all_fix_sites``). The fixing sites are all places that contribute opinions to the prim from ``strongest`` to
``weakest`` order. When no layer is provided to fix, by default will be the ``strongest``. If no indicated (as above) the preferred site will be the ``Root`` layer.
To change the preferred site to fix, we can add the ``at`` attribute to ``Suggestion``.

```{eval-rst}
.. literalinclude:: snippets/fix_at_site.py
   :language: python
   :linenos:
   :emphasize-lines: 21
```

The output will change the order now, and you should see the sublayer *first* (i.e. ``layer.usda``).

```{eval-rst}
.. literalinclude:: snippets/fix_at_site.out
   :language: none
   :linenos:
```

The previous tutorial should have helped you to:
- Create a custom Rule, generating an error and a suggestion to fix it.
- Run ValidationEngine with a specific rule.
- Run IssueFixer to fix specific issues and review the response.

## Frequently Asked Questions

**Are there any guards to make sure fixes are still relevant / don't collide?**

In our general practice we have noticed:
- *Fixing an issue may solve another issue*. If a consecutive suggestion may fail to be applied, we just keep the
exception in `FixResult` and continue execution. You will then decide the steps to take with `FixResult`.
- *Fixing an issue may generate another issue*. For the second case it is recommended to run `ValidationEngine` again,
to discover those cases. Think of it as an iterative process with help of an automated tool.

**Are fixes addressed in the root layer? strongest layer?**

Currently, some Issues would perform the suggestion on the strongest layer, while many on the root layer. We are
working into offer flexibility to decide in which layer aim the changes, while also offering a default layer for
automated workflows.
