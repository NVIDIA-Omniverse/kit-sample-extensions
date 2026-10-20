# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import json
import uuid
from contextlib import asynccontextmanager, contextmanager
from math import ceil
from typing import Callable, Optional, Tuple
from unittest.mock import ANY, Mock, PropertyMock, patch

import numpy as np
import omni.client
import omni.kit.test
from idl.connection.transport import TransportError
from idl.connection.transport.ws import WebSocketClient
from omni.discovery import DiscoverySearch
from omni.kit.ngsearch.api import (
    async_search,
    close_connection,
    get_embedding_hierarchy,
    get_embedding_hierarchy_multiserver,
    get_embeddings,
    get_prefixes,
    is_available,
    paginated_search,
    telemetry_event_click,
    telemetry_event_results_presented,
)
from omni.kit.ngsearch.client import NGSearchClient
from omni.kit.ngsearch.data import (
    S3Config,
    SearchItem,
    TelemetryContext,
)
from omni.kit.ngsearch.exceptions import HierarchyRetrievalUnavailable
from omni.ngsearch import NGSearchClient as IDLNGSearchClient
from omni.ngsearch.client import NGSearchService, StatusOnlyResponse, StatusType
from omni.ngsearch.data import (
    EmbeddingHierarchy,
    HierarchicalClustering,
    Path,
    PrefixResult,
    SearchItem,
    SearchQuery2,
)

from ..data import EmbeddingHierarchyResponse
from .data import mock_clusters, mock_hierarchy_nodes, sample_server_groups
from .helper import check_clusters


class AsyncMock(Mock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class TestNGSearchAPI(omni.kit.test.AsyncTestCase):
    async def test_instance(self):
        search_interface = NGSearchClient.get_instance()
        self.assertTrue(search_interface is not None)

    async def mock_find2_impl(self, owner, query, token, telemetry_context):
        mock_response = Mock()
        mock_response.status = StatusType.OK
        mock_response.paths = self._mock_search_results
        return mock_response

    async def mock_telemetry_event(self, *args, **kwargs) -> StatusOnlyResponse:
        return StatusOnlyResponse(status=StatusType.OK)

    async def mock_token_expired(self, *_, **__):
        mock_response = Mock()
        mock_response.status = StatusType.TokenExpired
        yield mock_response

    async def mock_compute_hierarchical_clustering(self, *_, **__) -> HierarchicalClustering:
        return HierarchicalClustering(
            version="1",
            status=StatusType.OK,
            hierarchy_nodes=json.dumps(mock_hierarchy_nodes),
        )

    async def mock_compute_hierarchical_clustering_raise_error(self, *_, **__) -> HierarchicalClustering:
        raise Exception("test error")

    async def mock_compute_hierarchical_clustering_raise_transport_error(self, *_, **__) -> HierarchicalClustering:
        raise TransportError("test error")

    async def mock_search_gen_2_impl(self, *args, **kwargs):
        batch_size = len(self._mock_search_gen_2_results)
        if "batch_size" in kwargs and kwargs["batch_size"]:
            batch_size = kwargs["batch_size"]

        n = int(ceil(len(self._mock_search_gen_2_results) / batch_size))
        for i in range(n):
            mock_response = Mock()
            mock_response.item_list = self._mock_search_gen_2_results[i * batch_size : (i + 1) * batch_size]
            mock_response.status = StatusType.OK
            yield mock_response

    async def mock_search_gen_2_impl_pass(self, *_, **__):
        """Generator that does not yield anything - just directly raise StopAsyncIteration"""
        for _ in []:
            yield None

    async def mock_search_gen_2_impl_unknown_error(self, *args, **kwargs):
        yield SearchItem(
            status=StatusType.UnknownError,
        )

    async def mock_search_gen_2_impl_unknown_error_on_s3(self, *args, query: SearchQuery2, **kwargs):
        if query.parent.startswith("/omniverse_server"):
            async for item in self.mock_search_gen_2_impl():
                yield item
        else:
            async for item in self.mock_search_gen_2_impl_unknown_error():
                yield item

    async def mock_search_gen_2_impl_raise_error_on_s3(self, *args, query: SearchQuery2, **kwargs):
        if query.parent.startswith("/omniverse_server"):
            async for item in self.mock_search_gen_2_impl():
                yield item
        else:
            async for item in self.mock_search_gen_2_impl_raise_error():
                yield item

    async def mock_search_gen_2_impl_raise_error(self, *args, **kwargs):
        def raise_error():
            raise Exception("test error")

        yield raise_error()

    async def mock_get_embedding_hierarchy_impl(self, *args, **kwargs) -> EmbeddingHierarchy:
        return EmbeddingHierarchy(
            version="1",
            status=StatusType.OK,
            clusters=json.dumps(
                dict(
                    search_items=self._mock_search_gen_2_results,
                    hierarchy_nodes=json.dumps(mock_clusters),
                )
            ),
            search_request_id=uuid.uuid4(),
        )

    async def mock_get_embedding_hierarchy_impl_raise_error(self, *args, **kwargs) -> EmbeddingHierarchy:
        raise Exception("test error")

    async def mock_get_embedding_hierarchy_impl_raise_transport_error(self, *args, **kwargs) -> EmbeddingHierarchy:
        raise TransportError("test error")

    async def mock_get_prefixes_impl(self, owner) -> PrefixResult:
        self._mock_prefixes_results = [
            "name",
            "description",
            "created_by",
            "size",
            "ext",
        ]
        return PrefixResult(version="1", prefixes=self._mock_prefixes_results, status=StatusType.OK)

    async def mock_refresh_auth_token_async(self, _) -> Tuple[omni.client.Result, str]:
        return omni.client.Result.OK, uuid.uuid4()

    async def mock_get_embeddings_impl(self, owner, queries):
        self._mock_embeddings_results = ["1351251205910295810289"]
        result = Mock()
        result.data = []
        for data in self._mock_embeddings_results:
            inner_result = Mock()
            inner_result.data = data
            result.data.append(inner_result)
        return result

    async def mock_find_impl(self, owner, interface, meta=None, capabilities={}):
        # Mock discovery's find with a fake transport
        mock_discovery = Mock()
        mock_discovery.transport = Mock()
        mock_discovery.transport.prepare = AsyncMock()
        mock_discovery.transport.close = AsyncMock()
        return mock_discovery

    async def mock_get_service_impl(self, *_, **__):
        # Mock discovery's find with a fake transport
        mock_discovery = Mock()
        mock_discovery.transport = Mock()
        mock_discovery.transport.prepare = AsyncMock()
        mock_discovery.transport.close = AsyncMock()
        return mock_discovery

    async def mock_auth_impl(self, url):
        mock_server_info = Mock()
        mock_server_info.auth_token = "ABCD_FAKETOKEN_ABCD"
        return omni.client.Result.OK, mock_server_info

    def mock_s3_buckets_impl(self):
        return {
            "ov-test-bucket.s3.fake-region.amazonaws.com": S3Config(
                url="https://ov-test-bucket.s3.fake-region.amazonaws.com",
                bucket_name="ov-test-bucket",
                region_name="fake-region",
                use_discovery=False,
                deepsearch_url="ws://fake-url:9999",
            ),
            "ov-test-bucket-2.s3.fake-region.amazonaws.com": S3Config(
                url="https://ov-test-bucket-2.s3.fake-region.amazonaws.com",
                bucket_name="ov-test-bucket-2",
                region_name="fake-region",
                use_discovery=False,
            ),
        }

    def mock_discover_ngsearch_s3_impl(self, *_, **__):
        return dict(host="fake-host", port=9999)

    def setup(self):
        def _path(uri: str):
            p = Path(uri=uri)
            return p

        self._mock_search_results = [
            _path("/foo.usd"),
            _path("/materials/fake.mdl"),
            _path("/folder/img.png"),
            _path("/foo2.usd"),
            _path("/materials/fake2.mdl"),
            _path("/folder/img2.png"),
            _path("/foo3.usd"),
            _path("/materials/fake3.mdl"),
            _path("/folder/img3.png"),
            _path("/foo4.usd"),
            _path("/materials/fake4.mdl"),
            _path("/folder/img4.png"),
            _path("/foo5.usd"),
            _path("/materials/fake5.mdl"),
            _path("/folder/img5.png"),
        ]

        def _search_item():
            return SearchItem(
                path=Path(uri="/test", score=np.random.rand()),
                embed=json.dumps(np.random.rand(512).tolist()),
            )

        self._mock_search_gen_2_results = [_search_item()] * 10

    async def mock_is_available_exception(self, *_):
        raise Exception("test error")

    async def test_get_prefixes(self):
        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(NGSearchService, "get_prefixes", autospec=True) as mock_service_get_prefixes,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl

            ### Get Prefixes Test
            mock_service_get_prefixes.side_effect = self.mock_get_prefixes_impl

            results = await get_prefixes("omniverse://ov-test/fake/folder")
            self.assertEqual(results, self._mock_prefixes_results)
            mock_service_get_prefixes.assert_called_once()

    async def test_get_embeddings(self):
        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(NGSearchService, "get_embeddings", autospec=True) as mock_service_get_embeddings,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl

            ### Get Emebddings Test
            mock_service_get_embeddings.side_effect = self.mock_get_embeddings_impl

            url = "omniverse://ov-test/fake/folder"
            queries = ["red rusty barrel"]
            results = await get_embeddings(queries, url)
            self.assertEqual(results, self._mock_embeddings_results)
            mock_service_get_embeddings.assert_called_once_with(ANY, queries)

    async def test_find2(self):
        self.setup()

        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(NGSearchService, "find2", autospec=True) as mock_service_find2,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl

            ### Find2 Test
            mock_service_find2.side_effect = self.mock_find2_impl

            result = await async_search("test", "omniverse://ov-test/fake/folder")

            self.assertEqual(result.paths, self._mock_search_results)
            self.assertEqual(result.status, StatusType.OK)

            mock_service_find2.assert_called_once_with(
                ANY,
                {"name": "test", "parent": "/fake/folder", "tags": ["test"]},
                token="ABCD_FAKETOKEN_ABCD",
                telemetry_context=None,
            )
            mock_server_info.assert_called_once_with("omniverse://ov-test/fake/folder")

    async def test_paginated_search(self):
        self.setup()

        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(NGSearchService, "search_gen_2", autospec=True) as mock_service_search_gen_2,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl

            ### Paginated Search Test
            mock_service_search_gen_2.side_effect = self.mock_search_gen_2_impl

            async for result in paginated_search("test", "omniverse://ov-test/fake/folder/"):
                self.assertEqual(result.status, StatusType.OK)
                self.assertEqual(result.item_list, self._mock_search_gen_2_results)
                self.assertTrue(result.item_list[0].url.startswith("omniverse://"))

    async def test_paginated_search_https_s3(self):
        self.setup()

        async with self.supported_url_experiment_setup():
            with patch.object(NGSearchService, "search_gen_2", autospec=True) as mock_service_search_gen_2:
                ### Paginated Search Test
                mock_service_search_gen_2.side_effect = self.mock_search_gen_2_impl

                async for result in paginated_search("test", "https://ov-test-bucket.s3.fake-region.amazonaws.com"):
                    self.assertEqual(result.status, StatusType.OK)
                    self.assertEqual(result.item_list, self._mock_search_gen_2_results)
                    self.assertTrue(result.item_list[0].url.startswith("https://"))

    async def test_paginated_search_s3(self):
        self.setup()

        async with self.supported_url_experiment_setup():
            with patch.object(NGSearchService, "search_gen_2", autospec=True) as mock_service_search_gen_2:
                ### Paginated Search Test
                mock_service_search_gen_2.side_effect = self.mock_search_gen_2_impl

                async for result in paginated_search("test", "s3://ov-test-bucket"):
                    self.assertEqual(result.status, StatusType.OK)
                    self.assertEqual(result.item_list, self._mock_search_gen_2_results)
                    self.assertTrue(result.item_list[0].url.startswith("s3://"))

    async def test_token_expired(self):
        self.setup()

        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(NGSearchService, "search_gen_2", autospec=True) as mock_service_search_gen_2,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl

            ### Paginated Search Test
            mock_service_search_gen_2.side_effect = self.mock_token_expired

            search_dir = "omniverse://ov-test/fake/folder/"
            host = omni.client.break_url(search_dir).host

            async for result in paginated_search("test", search_dir):
                self.assertEqual(result.status, StatusType.TokenExpired)
                self.assertIn(host, NGSearchClient.get_instance()._connections)
                self.assertIn(host, NGSearchClient.get_instance()._auth_tokens)
                await close_connection(search_dir)
                self.assertNotIn(host, NGSearchClient.get_instance()._connections)
                self.assertNotIn(host, NGSearchClient.get_instance()._auth_tokens)

    @contextmanager
    def get_embedding_hierarchy_context(
        self,
        get_embedding_hierarchy_n_calls: Optional[int] = None,
        mock_search_gen_2_impl: Optional[Callable] = None,
        mock_compute_hierarchical_clustering_side_effect: Optional[Callable] = None,
        mock_service_get_embedding_hierarchy_side_effect: Optional[Callable] = None,
    ):
        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(
                NGSearchService, "get_embedding_hierarchy", autospec=True
            ) as mock_service_get_embedding_hierarchy,
            patch.object(
                NGSearchService, "compute_hierarchical_clustering", autospec=True
            ) as mock_compute_hierarchical_clustering,
            patch.object(NGSearchService, "search_gen_2", autospec=True) as mock_service_search_gen_2,
            patch.object(omni.client, "refresh_auth_token_async", autospec=True) as mock_refresh_auth_token_async,
            patch(
                "omni.kit.ngsearch.client.NGSearchClient.s3_buckets",
                new_callable=PropertyMock,
            ) as mock_s3_buckets,
        ):
            ### Paginated Search Test
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl
            mock_refresh_auth_token_async.side_effect = self.mock_refresh_auth_token_async
            ### Paginated Search Test
            if mock_service_get_embedding_hierarchy_side_effect is None:
                mock_service_get_embedding_hierarchy.side_effect = self.mock_get_embedding_hierarchy_impl
            else:
                mock_service_get_embedding_hierarchy.side_effect = mock_service_get_embedding_hierarchy_side_effect
            if mock_compute_hierarchical_clustering_side_effect is None:
                mock_compute_hierarchical_clustering.side_effect = self.mock_compute_hierarchical_clustering
            else:
                mock_compute_hierarchical_clustering.side_effect = mock_compute_hierarchical_clustering_side_effect

            if mock_search_gen_2_impl is None:
                mock_service_search_gen_2.side_effect = self.mock_search_gen_2_impl
            else:
                mock_service_search_gen_2.side_effect = mock_search_gen_2_impl
            mock_s3_buckets.return_value = self.mock_s3_buckets_impl()

            yield

            if get_embedding_hierarchy_n_calls is not None:
                assert mock_service_get_embedding_hierarchy.call_count == get_embedding_hierarchy_n_calls

    async def test_get_embedding_hierarchy(self):
        self.setup()

        with self.get_embedding_hierarchy_context(get_embedding_hierarchy_n_calls=1):
            result = await get_embedding_hierarchy("test max:5", "omniverse://ov-test/fake/folder/")
            self.assertEqual(result.status, StatusType.OK)
            self.assertIsInstance(result.clusters, str)
            clusters = json.loads(result.clusters)
            hierarchy_nodes = json.loads(clusters["hierarchy_nodes"])
            check_clusters(hierarchy_nodes=hierarchy_nodes)

    async def test_get_embedding_hierarchy_multiserver_token_expired(self):
        self.setup()

        server_alias = "ov-test"

        with self.get_embedding_hierarchy_context(
            get_embedding_hierarchy_n_calls=0,
            mock_search_gen_2_impl=self.mock_token_expired,
        ):
            result = await get_embedding_hierarchy_multiserver(
                "test max:5",
                [
                    f"omniverse://{server_alias}/fake/folder/",
                    f"omniverse://{server_alias}/fake/folder/",
                ],
            )
            self.assertEqual(result.status, StatusType.TokenExpired)
            self.assertEqual(len(result.clusters["search_items"]), 0)

    async def test_get_embedding_hierarchy_multiserver(self):
        self.setup()

        server_alias = "ov-test"

        with self.get_embedding_hierarchy_context(get_embedding_hierarchy_n_calls=0):
            result = await get_embedding_hierarchy_multiserver(
                "test max:5",
                [
                    f"omniverse://{server_alias}/fake/folder/",
                    f"omniverse://{server_alias}/fake/folder/",
                ],
            )
            self.assertEqual(result.status, StatusType.OK)
            search_item: SearchItem
            for search_item in result.clusters["search_items"]:
                self.assertTrue(search_item.url.startswith("omniverse://"))
                broken_url = omni.client.break_url(search_item.url)
                # make sure URL is correctly populated with the provided server alias
                self.assertEqual(broken_url.host, server_alias)
                self.assertEqual(broken_url.scheme, "omniverse")

    async def test_get_embedding_hierarchy_multiserver_single(self):
        self.setup()

        for server_name in [
            f"omniverse://ov-test",
            f"https://ov-test-bucket.s3.fake-region.amazonaws.com",
        ]:
            with self.get_embedding_hierarchy_context(get_embedding_hierarchy_n_calls=1):
                result = await get_embedding_hierarchy_multiserver(
                    "test max:5",
                    [f"{server_name}/fake/folder/"],
                )
                self.assertEqual(result.status, StatusType.OK)
                search_item: SearchItem
                for search_item in result.clusters["search_items"]:
                    self.assertTrue(search_item["url"].startswith(f"{server_name}"))
                    broken_url = omni.client.break_url(search_item["url"])
                    # make sure URL is correctly populated with the provided server alias
                    self.assertEqual(broken_url.host, omni.client.break_url(server_name).host)
                    self.assertEqual(broken_url.scheme, omni.client.break_url(server_name).scheme)

    async def test_get_embedding_hierarchy_multiserver_error(self):
        self.setup()

        for search_gen_mock in [
            self.mock_search_gen_2_impl_unknown_error,
            self.mock_search_gen_2_impl_raise_error,
        ]:
            with self.subTest(search_gen_mock=search_gen_mock.__name__):
                with self.get_embedding_hierarchy_context(
                    get_embedding_hierarchy_n_calls=0,
                    mock_search_gen_2_impl=search_gen_mock,
                ):
                    result: EmbeddingHierarchyResponse = await get_embedding_hierarchy_multiserver(
                        "test max:5",
                        [
                            f"omniverse://ov-test",
                            f"https://ov-test-bucket.s3.fake-region.amazonaws.com",
                        ],
                    )
                    self.assertEqual(len(result.clusters["search_items"]), 0)
                    self.assertEqual(result.status, StatusType.UnknownError)

    async def test_get_embedding_hierarchy_multiserver_raise_error_on_clustering(self):
        self.setup()

        with self.get_embedding_hierarchy_context(
            mock_service_get_embedding_hierarchy_side_effect=self.mock_get_embedding_hierarchy_impl_raise_error,
            mock_compute_hierarchical_clustering_side_effect=self.mock_compute_hierarchical_clustering_raise_error,
        ):
            for paths in sample_server_groups:
                with self.subTest(paths=paths):
                    result: EmbeddingHierarchyResponse = await get_embedding_hierarchy_multiserver("test max:5", paths)
                    self.assertEqual(len(result.clusters["search_items"]), 0)
                    self.assertEqual(result.status, StatusType.UnknownError)

    async def test_get_embedding_hierarchy_multiserver_raise_transport_error_on_clustering(
        self,
    ):
        self.setup()

        with self.get_embedding_hierarchy_context(
            mock_service_get_embedding_hierarchy_side_effect=self.mock_get_embedding_hierarchy_impl_raise_transport_error,
            mock_compute_hierarchical_clustering_side_effect=self.mock_compute_hierarchical_clustering_raise_transport_error,
        ):
            for paths in sample_server_groups:
                with self.subTest(paths=paths):
                    with self.assertRaises(HierarchyRetrievalUnavailable):
                        _ = await get_embedding_hierarchy_multiserver("test max:5", paths)

    async def test_get_embedding_hierarchy_multiserver_search_method_pass(self):
        self.setup()

        with self.get_embedding_hierarchy_context(
            get_embedding_hierarchy_n_calls=0,
            mock_search_gen_2_impl=self.mock_search_gen_2_impl_pass,
        ):
            result: EmbeddingHierarchyResponse = await get_embedding_hierarchy_multiserver(
                "test max:5",
                [
                    f"omniverse://ov-test",
                    f"https://ov-test-bucket.s3.fake-region.amazonaws.com",
                ],
            )
            self.assertEqual(len(result.clusters["search_items"]), 0)
            self.assertEqual(result.status, StatusType.OK)

    async def test_get_embedding_hierarchy_multiserver_unknown_error_on_s3(self):
        self.setup()

        with self.get_embedding_hierarchy_context(
            get_embedding_hierarchy_n_calls=0,
            mock_search_gen_2_impl=self.mock_search_gen_2_impl_unknown_error_on_s3,
        ):
            result: EmbeddingHierarchyResponse = await get_embedding_hierarchy_multiserver(
                "test max:5",
                [
                    f"omniverse://ov-test/omniverse_server",
                    f"https://ov-test-bucket.s3.fake-region.amazonaws.com/s3_bucket",
                ],
                batch_size=5,
            )
            self.assertEqual(len(result.clusters["search_items"]), 5)
            self.assertEqual(result.status, StatusType.OK)

    async def test_get_embedding_hierarchy_multiserver_raise_error_on_s3(self):
        self.setup()

        with self.get_embedding_hierarchy_context(
            get_embedding_hierarchy_n_calls=0,
            mock_search_gen_2_impl=self.mock_search_gen_2_impl_raise_error_on_s3,
        ):
            result: EmbeddingHierarchyResponse = await get_embedding_hierarchy_multiserver(
                "test max:5",
                [
                    f"omniverse://ov-test/omniverse_server",
                    f"https://ov-test-bucket.s3.fake-region.amazonaws.com/s3_bucket",
                ],
                batch_size=5,
            )
            self.assertEqual(len(result.clusters["search_items"]), 5)
            self.assertEqual(result.status, StatusType.OK)

    async def test_telemetry_event_click(self):
        self.setup()

        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(NGSearchService, "telemetry_event_click", autospec=True) as mock_service_telemetry_event_click,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl

            ### Paginated Search Test
            mock_service_telemetry_event_click.side_effect = self.mock_telemetry_event

            result = await telemetry_event_click(
                query="description:blue ext:usd",
                url="omniverse://ov-test/fake/folder",
                n=8,
                n_results_total=32,
                asset_id=1,
                asset_rank=2,
                click_order=3,
                time_to_present=0.1,
                time_to_click=1.0,
                query_time=0.1,
                search_request_id="some_id",
                telemetry_context=TelemetryContext(
                    app_name="create",
                    app_version="1.2.3",
                    ui_name="content_browser",
                    ui_version="1.0.0",
                    session_id=uuid.uuid4(),
                ),
            )

            self.assertEqual(result.status, StatusType.OK)

    async def test_telemetry_event_results_presented(self):
        self.setup()

        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(
                NGSearchService, "telemetry_event_results_presented", autospec=True
            ) as mock_service_telemetry_event_results_presented,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl

            ### Paginated Search Test
            mock_service_telemetry_event_results_presented.side_effect = self.mock_telemetry_event

            result = await telemetry_event_results_presented(
                query="description:blue ext:usd",
                url="omniverse://rc.ov.nvidia.com/Projects",
                n=8,
                n_results_total=32,
                time_to_present=0.1,
                query_time=0.1,
                thumbnail_load_time=[1] * 32,
                search_request_id="some_id",
                telemetry_context=TelemetryContext(
                    app_name="create",
                    app_version="1.2.3",
                    ui_name="content_browser",
                    ui_version="1.0.0",
                    session_id=uuid.uuid4(),
                ),
            )

            self.assertEqual(result.status, StatusType.OK)

    @asynccontextmanager
    async def supported_url_experiment_setup(self):
        with (
            patch.object(DiscoverySearch, "find", autospec=True) as mock_discovery_find,
            patch.object(omni.client, "get_server_info_async", autospec=True) as mock_server_info,
            patch.object(WebSocketClient, "prepare", autospec=True) as mock_client_prepare,
            patch.object(WebSocketClient, "close", autospec=True) as mock_client_close,
            patch.object(NGSearchService, "get_prefixes", autospec=True) as mock_service_get_prefixes,
            patch.object(NGSearchClient, "_discover_ngsearch_s3", autospec=True) as mock_discover_ngsearch_s3,
            patch.object(IDLNGSearchClient, "get_service", autospec=True) as mock_get_service,
            patch(
                "omni.kit.ngsearch.client.NGSearchClient.s3_buckets",
                new_callable=PropertyMock,
            ) as mock_s3_buckets,
        ):
            mock_client_prepare.return_value = AsyncMock()
            mock_client_close.return_value = AsyncMock()
            mock_discovery_find.side_effect = self.mock_find_impl
            mock_server_info.side_effect = self.mock_auth_impl
            mock_discover_ngsearch_s3.side_effect = self.mock_discover_ngsearch_s3_impl
            mock_get_service.side_effect = self.mock_get_service_impl

            ### Get Prefixes Test
            mock_service_get_prefixes.side_effect = self.mock_get_prefixes_impl
            mock_s3_buckets.return_value = self.mock_s3_buckets_impl()
            yield mock_service_get_prefixes

    async def test_supported_urls(self):
        async with self.supported_url_experiment_setup() as mock_service_get_prefixes:
            # omniverse prefix
            for ind, url in enumerate(
                [
                    "omniverse://ov-test/fake/folder",
                    "s3://ov-test-bucket/fake/folder",
                    "https://ov-test-bucket.s3.fake-region.amazonaws.com/fake/folder",
                ]
            ):
                with self.subTest(url=url):
                    results = await get_prefixes(url)
                    self.assertEqual(results, self._mock_prefixes_results)
                    self.assertEqual(ind + 1, mock_service_get_prefixes.call_count)

    async def test_supported_urls_invalid_schema(self):
        async with self.supported_url_experiment_setup() as mock_service_get_prefixes:
            # https S3 prefix
            with self.assertRaises(NotImplementedError):
                _ = await get_prefixes("invalid_schema://ov-test-bucket.s3.fake-region.amazonaws.com/fake/folder")
            mock_service_get_prefixes.assert_not_called()

    async def test_supported_urls_incorrect_s3_setup(self):
        async with self.supported_url_experiment_setup():
            # it is expected to fail discovery, as there is no deepsearch URL defined
            success = await NGSearchClient.get_instance()._discovery_and_authorization(
                "s3://ov-test-bucket-2/fake/folder"
            )
            self.assertFalse(success)

    async def test_is_available_exception(self):
        """Test to make sure exception in is_available method are properly handled."""
        self.setup()

        with patch.object(NGSearchClient, "is_available", autospec=True) as mock_is_available:
            mock_is_available.side_effect = self.mock_is_available_exception

            self.assertFalse(await is_available("omniverse://fake-url"))

    async def test_preset_s3_buckets_loading(self):
        client = NGSearchClient.get_instance()
        self.assertIsNone(client._s3_buckets)
        s3_buckets = client.s3_buckets
        self.assertIsNotNone(client._s3_buckets)
        self.assertEqual(s3_buckets, client._s3_buckets)
