import os
import tempfile

import omni.client.utils as clientutils
import omni.kit.app
import omni.kit.test
import omni.usd
from omni.kit.tool.asset_importer.utils import Utils as importer_utils


class TestUtils(omni.kit.test.AsyncTestCase):
    async def test_utils(self):
        absolute_path = importer_utils.compute_absolute_path("omniverse://test/", True, "file.usd", False)
        self.assertEqual(absolute_path, "omniverse://test/file.usd")

        absolute_path = importer_utils.compute_absolute_path("omniverse://test", True, "file.usd", False)
        self.assertEqual(absolute_path, "omniverse://test/file.usd")

        absolute_path = importer_utils.compute_absolute_path("omniverse://test/", False, "file.usd", False)
        self.assertEqual(absolute_path, "omniverse://test/file.usd")

        absolute_path = importer_utils.compute_absolute_path("omniverse://server/test.usd", False, "file.usd", False)
        self.assertEqual(absolute_path, "omniverse://server/file.usd")

        absolute_path = importer_utils.compute_absolute_path(
            "omniverse://other/", True, "omniverse://test/file.usd", False
        )
        self.assertEqual(absolute_path, "omniverse://test/file.usd")

        absolute_path = importer_utils.compute_absolute_path(
            "omniverse://other/", True, "omniverse://test/file.usd", False
        )
        self.assertEqual(absolute_path, "omniverse://test/file.usd")

        # Creates a file under a two level folder.
        with tempfile.TemporaryDirectory() as f1:
            from pathlib import Path

            f1 = str(Path(f1).resolve())
            f2 = os.path.join(f1, "f2")
            os.makedirs(f2)
            new_file = os.path.join(f2, "test.txt")
            with open(new_file, "w+") as f:
                f.write("random text")

            absolute_paths, relative_paths = await importer_utils.list_folder_async(f1)
            self.assertEqual(len(absolute_paths), 1)
            self.assertEqual(len(relative_paths), 1)
            self.assertEqual(absolute_paths, [clientutils.normalize_url(new_file)])
            self.assertEqual(relative_paths, [f"{os.path.basename(f1)}/f2/test.txt"])
