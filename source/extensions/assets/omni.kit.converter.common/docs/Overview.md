# Omniverse CAD Converter Common [omni.kit.converter.common]

# Overview

CAD Converter Common serves as a utility module designed for sharing code across different CAD Converter Extensions, promoting code reusability.

## Copying converted output

Use the public async `copy_output_assets()` utility to upload a staged USD and its generated textures and referenced USD files:

```python
from omni.kit.converter.common import copy_output_assets

await copy_output_assets(staged_usd_path, "omniverse://server/Projects/model.usda")
```

`staged_usd_path` must point to a local, writable conversion output. Use the same filename for the source and destination USD. The function rewrites and saves the staged layers with relative destination paths, copies dependencies into a unique asset folder, and uploads the root USD last. Use disposable staging files because their references are changed in place.

The function returns no value. Save or upload failures raise exceptions that the caller must handle. Keep the uploaded asset folder with the root USD. Previous exports and partially uploaded asset folders are not automatically removed.

## Deprecations and Removals

- Removed NVCF utility functions, and related test artifacts



# Licensing Terms of Use and Third-Party Notices
`omni.kit.converter.common` is governed by the
[NVIDIA Software License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)
and the [Product Specific Terms for NVIDIA AI Products](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products/).
Customers may redistribute the Omniverse CAD Converter as permitted by those terms.
By downloading or using NVIDIA Omniverse, you agree to the terms. See the
[Omniverse License Agreement](https://docs.omniverse.nvidia.com/dev-guide/latest/common/NVIDIA_Omniverse_License_Agreement.html).
