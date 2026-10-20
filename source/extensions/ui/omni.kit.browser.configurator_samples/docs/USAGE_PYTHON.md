# Usage Examples

## Get Extension Instance and Access Model

```python
from omni.kit.browser.configurator_samples import get_instance

# Get the singleton instance of the Sample Browser Extension
browser_extension = get_instance()

# Access the model to manage sample browser data
model = browser_extension.get_model()

# Access the window (if it has been created)
window = browser_extension.get_window()
```

## Register and Unregister Sample Folder

```python
from omni.kit.browser.configurator_samples import register_sample_folder, unregister_sample_folder

test_folder = "/custom_folder"

# Register a new sample folder
register_sample_folder(test_folder, "Custom Test")

# Unregister the sample folder
# unregister_sample_folder(test_folder)
```
