import omni.asset_validator.core

for requirement in omni.asset_validator.core.RequirementsRegistry().requirements:
    print(requirement.code)
