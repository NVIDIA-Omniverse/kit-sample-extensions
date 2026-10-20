## Copyright (c) 2018-2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from pathlib import Path

import omni.kit.app
import omni.kit.test


class TestSearch(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        """Before running each test"""
        pass

    async def tearDown(self):
        """After running each test"""
        pass

    async def test_search(self):
        """Searching current file"""
        from ..search_file_model import SearchFileModel

        dir_name = Path(__file__).parent
        file_name = Path(__file__).name

        model = SearchFileModel(search_text=f"{file_name}", current_dir=f"{dir_name}")

        # Delay to let omni.client find something
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        result = model.items

        # Found __file__
        self.assertEqual(len(result), 1)
        self.assertEqual(Path(result[0].path), Path(__file__))
        self.assertEqual(result[0].name, file_name)
