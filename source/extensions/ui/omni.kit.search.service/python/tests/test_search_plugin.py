import asyncio
import logging
from datetime import datetime
from typing import Dict
from unittest.mock import ANY, Mock, patch

import carb
import omni.client
import omni.discovery
import omni.kit.ngsearch.api
import omni.kit.test
import omni.search.client
from idl.connection.transport import Client
from idl.connection.transport.ws import WebSocketClient
from omni.client import ServerInfo
from omni.kit.search_core import SearchLifetimeObject
from omni.ngsearch.data import SearchResult as NGSearchResult
from omni.search.client import Search as SearchInterface
from omni.search.data import Path, SearchResult, StatusType

from ..scripts.searchservice_client import SearchServiceClient
from ..scripts.searchservice_item import SearchServiceItem
from ..scripts.searchservice_model import NGSearchServiceModel

try:
    # introduced in python 3.8
    from unittest.mock import AsyncMock
except ImportError:

    class AsyncMock(Mock):
        async def __call__(self, *args, **kwargs):
            return super(AsyncMock, self).__call__(*args, **kwargs)


class TestSearchPlugin(omni.kit.test.AsyncTestCase):
    async def mock_is_available_impl(self, url: str):
        return True

    async def mock_is_not_available_impl(self, url: str):
        return False

    async def mock_search_get_prefixes_impl(self, url: str):
        self._search_prefixes = ["name", "fake", "prefix"]
        return {"prefixes": self._search_prefixes}

    async def mock_ngsearch_get_prefixes_impl(self, url: str):
        self._ngsearch_prefixes = ["description", "name", "fake", "prefix"]
        return self._ngsearch_prefixes

    async def mock_async_search_impl(self, query: str, url: str) -> NGSearchResult:
        return NGSearchResult(status=StatusType.OK, paths=self._mock_search_results)

    async def mock_find2_impl(self, *args, **kwargs) -> SearchResult:
        return SearchResult(status=StatusType.OK, paths=self._mock_search_results)

    async def mock_find_impl(self, *_, capabilities: Dict[str, int], **kwargs) -> SearchInterface:
        # Mock discovery's find with a fake transport
        mock_discovery = SearchInterface(transport=Client())
        mock_discovery.transport.prepare = AsyncMock()
        mock_discovery.transport.close = AsyncMock()
        # NOTE: This is the regression test for OM-86707
        #  it makes sure capabilities are properly set on the client side
        #  to make sure client works with earlier versions of the server
        self.assertIn("find2", capabilities)
        self.assertIn("get_prefixes", capabilities)
        self.assertGreaterEqual(capabilities["find2"], 2)
        self.assertGreaterEqual(capabilities["get_prefixes"], 0)
        return mock_discovery

    async def mock_find_impl_unavailable(self, *_, capabilities: Dict[str, int], **kwargs) -> SearchInterface:
        # Mock discovery's find with a fake transport
        mock_discovery = SearchInterface(transport=Client())
        mock_discovery.transport = None
        return mock_discovery

    async def mock_return_none(self, *args, **kwargs):
        return None

    def mock_log_warn(self, *args, **kwargs):
        logging.warning(*args, **kwargs)

    async def mock_auth_impl(self, url: str):
        mock_server_info = ServerInfo
        mock_server_info.auth_token = self._mock_auth_token
        return omni.client.Result.OK, mock_server_info

    def setup(self):
        self.url = "omniverse://test_nucleus_server/Projects/DeepSearch/"
        self.query = "blue car"

        self._mock_auth_token = "ABCD_FAKETOKEN_ABCD"

        mock_item = Path(modified=datetime.now().ctime(), size=1, uri="/Projects/DeepSearch/foo.usd")

        self._mock_search_results = [mock_item] * 6

        item = SearchServiceItem(
            "omniverse://test_nucleus_server/Projects/DeepSearch/",
            "foo.usd",
            date=datetime.strptime(mock_item.modified, "%c"),
            size=mock_item.size,
            is_folder=False,
        )

        self._mock_search_items = [item] * 6

    async def test_search(self):
        self.setup()

        # TODO make sure this tests when omni.kit.ngsearch is available
        with (
            patch.object(omni.kit.ngsearch.api, "is_available", autospec=True) as mock_is_not_available,
            patch.object(omni.discovery.DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.discovery.DiscoverySearch, "close", autospec=True) as mock_discovery_close,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(omni.search.client.Search, "find2", autospec=True) as mock_find2,
            patch.object(omni.search.client.Search, "get_prefixes", autospec=True) as mock_get_prefixes,
        ):
            mock_is_not_available.side_effect = self.mock_is_not_available_impl
            mock_discovery_close.side_effect = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_server_info.side_effect = self.mock_auth_impl
            mock_find2.side_effect = self.mock_find2_impl
            mock_get_prefixes.side_effect = self.mock_search_get_prefixes_impl

            mock_callback = Mock()
            obj = SearchLifetimeObject(callback=mock_callback)
            model = NGSearchServiceModel(search_text=self.query, current_dir=self.url, search_lifetime=obj)
            obj = None

            await asyncio.sleep(0.1)

            mock_find2.assert_called_once_with(
                ANY,
                {
                    "name": self.query,
                    "parent": "/Projects/DeepSearch/",
                    "tags": [self.query],
                },
                token=self._mock_auth_token,
            )

            mock_callback.assert_called_once()

            self.assertEqual(len(model.items), len(self._mock_search_items))
            for i in range(len(model.items)):
                self.assertEqual(model.items[i].path, self._mock_search_items[i].path)

            prefixes = await model.get_prefixes(self.url)
            self.assertEqual(prefixes, self._search_prefixes)

    async def test_search_service_not_found(self):
        self.setup()

        # TODO make sure this tests when omni.kit.ngsearch is available
        with (
            patch.object(omni.kit.ngsearch.api, "is_available", autospec=True) as mock_is_not_available,
            patch.object(omni.discovery.DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(omni.search.client.Search, "find2", autospec=True) as mock_find2,
        ):
            search_service_instance = SearchServiceClient.get_instance()
            # clear previous connections if any
            # search_service_instance._connection = None
            # search_service_instance._current_server = None
            search_service_instance.__del__()
            SearchServiceClient.__instance = None
            search_service_instance = SearchServiceClient.get_instance()

            mock_is_not_available.side_effect = self.mock_is_not_available_impl
            mock_discovery_find.side_effect = self.mock_find_impl_unavailable
            mock_server_info.side_effect = self.mock_auth_impl
            mock_find2.side_effect = self.mock_find2_impl

            mock_callback = Mock()
            obj = SearchLifetimeObject(callback=mock_callback)
            model = NGSearchServiceModel(search_text=self.query, current_dir=self.url, search_lifetime=obj)
            obj = None

            await asyncio.sleep(0.1)

            mock_find2.assert_not_called()
            mock_callback.assert_called_once()

            self.assertEqual(len(model.items), 0)
            prefixes = await model.get_prefixes(self.url)
            self.assertEqual(prefixes, [])

    async def test_ngsearch(self):
        self.setup()

        with (
            patch.object(omni.kit.ngsearch.api, "get_prefixes", autospec=True) as mock_get_prefixes,
            patch.object(omni.kit.ngsearch.api, "is_available", autospec=True) as mock_is_available,
            patch.object(omni.kit.ngsearch.api, "async_search", autospec=True) as mock_async_search,
        ):
            mock_get_prefixes.side_effect = self.mock_ngsearch_get_prefixes_impl
            mock_is_available.side_effect = self.mock_is_available_impl
            mock_async_search.side_effect = self.mock_async_search_impl

            mock_callback = Mock()
            obj = SearchLifetimeObject(callback=mock_callback)
            model = NGSearchServiceModel(search_text=self.query, current_dir=self.url, search_lifetime=obj)
            obj = None

            await asyncio.sleep(0.1)

            mock_callback.assert_called_once()
            mock_is_available.assert_called()

            self.assertEqual(len(model.items), len(self._mock_search_items))
            for i in range(len(model.items)):
                self.assertEqual(model.items[i].path, self._mock_search_items[i].path)

            prefixes = await model.get_prefixes(self.url)
            self.assertEqual(prefixes, self._ngsearch_prefixes)

    async def test_search_unavailable(self):
        self.setup()

        # TODO make sure this tests when omni.kit.ngsearch is available
        with (
            patch.object(omni.kit.ngsearch.api, "is_available", autospec=True) as mock_is_not_available,
            patch.object(omni.discovery.DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.discovery.DiscoverySearch, "close", autospec=True) as mock_discovery_close,
            patch.object(omni.search.client.Search, "find2", autospec=True) as mock_find2,
            patch.object(omni.search.client.Search, "get_prefixes", autospec=True) as mock_get_prefixes,
            patch.object(carb, "log_warn", autospec=True) as mock_log_warn,
        ):
            search_service_instance = SearchServiceClient.get_instance()
            # clear previous connections if any
            search_service_instance._connection = None
            search_service_instance._current_server = None
            search_service_instance._warned = {}

            self.assertEqual(len(search_service_instance._warned), 0)

            mock_is_not_available.side_effect = self.mock_is_not_available_impl
            mock_discovery_close.side_effect = AsyncMock()
            mock_discovery_find.side_effect = self.mock_return_none
            mock_find2.side_effect = self.mock_find2_impl
            mock_get_prefixes.side_effect = self.mock_search_get_prefixes_impl
            mock_log_warn.side_effect = self.mock_log_warn

            mock_callback = Mock()
            obj = SearchLifetimeObject(callback=mock_callback)
            model = NGSearchServiceModel(search_text=self.query, current_dir=self.url, search_lifetime=obj)
            obj = None

            await asyncio.sleep(0.5)
            mock_find2.assert_not_called()
            mock_callback.assert_called_once()
            self.assertEqual(mock_discovery_find.call_count, 1)
            self.assertEqual(len(search_service_instance._warned), 1)
            # make sure only two message have been printed to the std
            self.assertEqual(mock_log_warn.call_count, 2)

            await model.get_prefixes(self.url)
            self.assertEqual(len(search_service_instance._warned), 1)
            self.assertEqual(mock_discovery_find.call_count, 2)
            # make sure that there were no new message printed to std
            self.assertEqual(mock_log_warn.call_count, 2)
