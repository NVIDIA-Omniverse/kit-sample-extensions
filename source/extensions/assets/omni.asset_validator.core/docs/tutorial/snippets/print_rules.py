import omni.asset_validator.core

rules: list[str] = []
for category in omni.asset_validator.core.ValidationRulesRegistry.categories():
    for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category=category):
        rules.append(rule.__name__)

rules.sort()
for rule in rules:
    print(rule)
