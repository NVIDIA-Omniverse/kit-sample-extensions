import asyncio
from unittest.mock import Mock, patch

import omni.kit.ngsearch.api
import omni.kit.test
from omni.kit.search_core import SearchLifetimeObject

from ..scripts.searchservice_model import NGSearchServiceModel


class TestSearchPlugin(omni.kit.test.AsyncTestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.url = "omniverse://test_nucleus_server/Projects/DeepSearch/"
        self.query = "blue car"

    def get_search_model(self) -> NGSearchServiceModel:
        mock_callback = Mock()
        obj = SearchLifetimeObject(callback=mock_callback)
        model = NGSearchServiceModel(search_text=self.query, current_dir=self.url, search_lifetime=obj)
        obj = None
        return model

    async def test_get_prefixes(self) -> None:
        """Regression test for: https://omniverse-jirasw.nvidia.com/browse/OMFP-3284"""
        model = self.get_search_model()
        response = await model.get_prefixes(self.url)
        self.assertEqual(response, [])

    async def test_list(self) -> None:
        """Regression test for: https://omniverse-jirasw.nvidia.com/browse/OMFP-3284"""
        model = self.get_search_model()
        with (
            patch.object(NGSearchServiceModel, "_search", autospec=True) as mock_search,
            patch.object(NGSearchServiceModel, "_ngsearch", autospec=True) as mock_ngsearch,
        ):
            await model._NGSearchServiceModel__list()
            mock_search.assert_called()
            mock_search.assert_awaited()
            mock_ngsearch.assert_not_called()

    async def test_cancel_during_discovery(self) -> None:
        """Cancelling a search while ngsearch discovery runs must not start the fallback search, and must release
        the search lifetime object.

        ngsearch is_available() returns False when cancelled. The fallback search then started new discovery
        tasks after Kit's shutdown cancelled all tasks: "Task was destroyed but it is pending!".
        The task is cancelled directly, as Kit's shutdown and a newer search do, without destroy().
        """
        discovering = asyncio.Event()

        async def is_available_swallowing_cancel(url: str) -> bool:
            discovering.set()
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                return False
            return True

        with (
            patch.object(omni.kit.ngsearch.api, "is_available", side_effect=is_available_swallowing_cancel),
            patch.object(NGSearchServiceModel, "_search", autospec=True) as mock_search,
            patch.object(NGSearchServiceModel, "_ngsearch", autospec=True) as mock_ngsearch,
        ):
            model = self.get_search_model()
            await asyncio.wait_for(discovering.wait(), timeout=5)
            task = model._list_task
            task.cancel()
            await asyncio.wait([task], timeout=5)
            self.assertTrue(task.done())
            mock_search.assert_not_called()
            mock_ngsearch.assert_not_called()
            self.assertIsNone(model._search_lifetime)
            model.destroy()
