# Usage Examples

## Create a Custom Material Browser

```python
import omni.ui as ui
from omni.kit.browser.folder.core import TreeFolderBrowserWidget
from omni.kit.browser.material import MaterialDetailDelegate, MaterialDetailItem, MaterialFile, MaterialBrowserModel

window = ui.Window("Custom Material Browser", width=800, height=600)
model = MaterialBrowserModel()
with window.frame:
    TreeFolderBrowserWidget(
        model,
        detail_delegate=MaterialDetailDelegate(model)
    )
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.browser.material/data/docs_images/custom_material_browser.png
---
align: center
---
```
