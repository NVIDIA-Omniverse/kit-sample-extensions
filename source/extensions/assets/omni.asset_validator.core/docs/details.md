# Validation Rules by Category

Several categories of **validation rules** are defined in this core module. These include:
- The **Basic** rules from Pixar (i.e. the default `usdchecker` rules).
- A few NVIDIA developed rules that we plan to contribute back to the **Basic** set.
- Some Omniverse specific rules that apply to all Omniverse apps. These will be available under several **Omni:** prefixed categories.

# Writing Your Own Rules

Any external client code can define new rules and register them with the system. Simply add `omni.asset_validator.core` as a dependency of your project (i.e. your Kit extension or other python module), derive a new class from `BaseRuleChecker`, and use the `ValidationRulesRegistry` to categorize your rule with the system. See the [Core Python API](./api) for thorough details and example code. We even provide a small [Testing API](./api) to ease unit testing new rules against known USD layer files.

```{eval-rst}
.. important::
  Put extra thought into your category name, your class name, your ``GetDescription()`` implementation, and the messages in any errors, warnings, or failures that your rule generates at runtime. These are the user-facing portions of your rule, and many users will appreciate natural language over engineering semantics.
```

# Running The Validation Engine

Validation can be run synchronously (blocking) via `ValidationEngine.validate()`, or asynchronously via either `ValidationEngine.validate_async()` or `ValidationEngine.validate_with_callbacks()`. Currently validation _within_ an individual layer file or `Usd.Stage` is synchronous. This may become asynchronous in the future if it is merited.

Validation `Issues` are captured in a `Results` container. `Issues` vary in severity (Error, Failure, Warning) and will provide detailed messages explaining the problem. Optionally, they may also provide detail on where the issue occurred in the `Usd.Stage` and a suggestion (callable python code) for how it can be fixed automatically.

# Fixing Issues Automatically

Once validation `Results` have been obtained, they can be displayed for a user as plain text, but we also provide an automatic `IssueFixer` for some `Issues`. It is up to each individual rule to define the suggested fix via a python callable. See the [Core Python API](./api) for more details.


# Configuring Rules With Carbonite Settings

As with many Omniverse tools, `omni.asset_validator.core` is configurable at runtime using Carbonite settings. The following settings can be used to customize which rules are enabled/disabled for a particular app, company, or team.

## Settings
- `enabledCategories`/`disabledCategories` are lists of of glob style patterns matched against registered categories. Categories can be force-enabled using an exact match (no wildcards) in `enabledCategories`.
- `enabledRules`/`disabledRules` are lists of of glob style patterns matched against class names of registered rules. Rules can be force-enabled using an exact match (no wildcards) in `enabledRules`.

```{eval-rst}
.. tip::
    These settings only affect a default-constructed `ValidationEngine`. Using the Python API, client code may further configure a `ValidationEngine` using `enableRule()`. In such cases, the rules may not even be registered with the `ValidationRulesRegistry`.
```

# API and Changelog

We provide a thorough public API for the core validation framework and a minimal public testing API to assist clients in authoring new rules.

```{eval-rst}
.. toctree::
    :maxdepth: 1

    Python API <api>
    Rules <rules>
    CHANGELOG.md
```
