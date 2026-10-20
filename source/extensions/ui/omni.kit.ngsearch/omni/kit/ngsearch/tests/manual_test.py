# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import functools
import json
import os
import traceback
import unittest
from typing import Callable, Dict, List

import carb
import omni.client
from omni.kit.ngsearch.api import (
    NGSearchClient,
    TelemetryContext,
    async_search,
    close_connection,
    get_embedding_hierarchy,
    get_embedding_hierarchy_multiserver,
    get_prefixes,
    is_available,
    paginated_search,
    telemetry_event_click,
    telemetry_event_results_presented,
)
from omni.kit.ngsearch.client import client_ping
from omni.kit.ngsearch.data import Path, SearchItem
from omni.kit.ngsearch.tests.helper import check_clusters
from omni.ngsearch.client import StatusType

OUTPUT_FUNCTION = os.getenv("OUTPUT_FUNCTION", "carb")

if OUTPUT_FUNCTION == "print":
    print_fn = print
elif OUTPUT_FUNCTION == "carb":
    print_fn = carb.log_info
else:
    print_fn = carb.log_info

PASSED_TESTS = {}
TESTS_WITH_EXCEPTIONS = {}
CANCELLED_TESTS = {}

TELEMETRY_CONTEXT = TelemetryContext(
    app_name="Manual Extension Test",
    app_version="1.2.3",
    ui_name="No UI (manual test)",
    ui_version="1.0.0",
    session_id="a823d92a-4ed3-4618-956e-0c560039b310",
)


def check_samples(samples: List[Dict]) -> None:
    # recursively check that all clusters have all the proper fields in
    # place
    for sample in samples:
        item = SearchItem(**sample)
        path = Path(**item.path)
        assert path.uri is not None
        assert item.url is not None
        # im = mu.image_from_base64(item.image)
        # self.assertIsInstance(
        #     im,
        #     (
        #         JpegImagePlugin.JpegImageFile,
        #         PngImagePlugin.PngImageFile,
        #     ),
        # )


def handle_exception(func: Callable):
    """
    Decorator to print exception in async functions
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        global PASSED_TESTS, TESTS_WITH_EXCEPTIONS, CANCELLED_TESTS
        try:
            print_fn(f"-- Starting: {func.__name__} ------------------------")
            res = await func(*args, **kwargs)
            PASSED_TESTS[func.__name__] = PASSED_TESTS.get(func.__name__, 0) + 1
            print_fn(f"-- Completed Successfully: {func.__name__} ----------")
            return res
        except asyncio.CancelledError:
            CANCELLED_TESTS[func.__name__] = CANCELLED_TESTS.get(func.__name__, 0) + 1
            print_fn(f"-- !!! Cancelled: {func.__name__} ----------")
            carb.log_warn("Task was cancelled")
        except Exception as e:
            TESTS_WITH_EXCEPTIONS[func.__name__] = TESTS_WITH_EXCEPTIONS.get(func.__name__, []) + [e]
            print_fn(f"-- !!! Exception: {func.__name__} ----------")
            carb.log_error(f"Exception when async '{func}'")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

    return wrapper


class ManualCheck(unittest.TestCase):
    """Example code:

    from omni.kit.ngsearch.tests.manual_test import ManualCheck
    import asyncio

    async def tests():

        await ManualCheck().run_all()

    asyncio.ensure_future(tests())
    """

    @handle_exception
    async def run_multiserver(self, url_list: List[str]):
        await self.get_embedding_hierarchy_multiserver("red rusty barrel", url_list)

    async def get_embedding_hierarchy_multiserver(self, query, url_list: List[str]):
        batch_size = 32

        query = f"{query} max:{batch_size}"

        print_fn(f"Testing hierarchy retrieval on: {url_list} with query:{query}.")
        result = await get_embedding_hierarchy_multiserver(query, url_list=url_list, return_images=True)

        self.assertEqual(result.status, StatusType.OK)
        clusters: List[dict] = result.clusters
        samples = clusters["search_items"]
        hierarchy_nodes = json.loads(clusters["hierarchy_nodes"])
        check_clusters(hierarchy_nodes=hierarchy_nodes)
        check_samples(samples=samples)

    async def run_all(self, url: str):
        """Run all tests."""

        print_fn(f"Running all manual tests for {url}")
        print_fn("------------------------")

        await self.test_close_connection(url)

        await self.test_async_search('description:"red rusty barrel"', url)
        await self.test_paginated_search("red rusty barrel", url)
        await self.test_paginated_search_with_projections("red rusty barrel", url)
        await self.test_get_prefixes(url)

        # ######################################
        # # test embedding hierarchy retrieval #
        # ######################################

        await self.test_get_embedding_hierarchy("red rusty barrel", url)

        # ##############################
        # # test some telemetry events #
        # ##############################

        # processed event
        await self.test_telemetry_event_processed("manual test query", url)
        # clicked event
        await self.test_telemetry_event_clicked("manual test query", url)
        # clicked event within the search request
        await self.test_paginated_search_with_click("red rusty barrel", url)

        # ####################################################
        # # Test some corner cases and connection recreation #
        # ####################################################

        await self.test_connection_recreation("red rusty barrel", url)

    @staticmethod
    def print_test_stats():
        global PASSED_TESTS, TESTS_WITH_EXCEPTIONS, CANCELLED_TESTS

        total_passed = sum(list(PASSED_TESTS.values()))
        total_cancelled = sum(list(CANCELLED_TESTS.values()))
        total_exceptions = sum([len(t) for t in TESTS_WITH_EXCEPTIONS.values()])

        print_fn("\n-- STATS -------------------------")
        total = total_passed + total_exceptions + total_cancelled
        print_fn(f"> Passed:     {total_passed} / {total} ({total_passed / total * 100:.01f}%)")
        print_fn(f"> Exceptions: {total_exceptions} / {total} ({total_exceptions / total * 100:.01f}%)")
        print_fn(f"> Cancelled:  {total_cancelled} / {total} ({total_cancelled / total * 100:.01f}%)")
        print_fn("----------------------------------")

    @handle_exception
    async def test_close_connection(self, url: str):
        print_fn(f"Check availability: {url}")
        self.assertTrue(await is_available(url))
        print_fn(f"Close connection: {url}")
        await close_connection(url)
        host = omni.client.break_url(url).host
        self.assertNotIn(host, NGSearchClient.get_instance()._connections)
        self.assertTrue(await is_available(url))

    @handle_exception
    async def test_get_prefixes(self, url: str):
        print_fn(f"Testing get_prefixes on: {url}")
        prefixes = await get_prefixes(url)
        print_fn(f"Prefixes: {prefixes}")
        self.assertTrue(
            set(
                [
                    "name",
                    "-name",
                    "ext",
                    "-ext",
                    "max",
                    "path",
                    "tag",
                    "-tag",
                    "larger_than",
                    "smaller_than",
                    "description",
                    "-description",
                    "image",
                    "created_by",
                    "-created_by",
                    "modified_by",
                    "-modified_by",
                    "created_before",
                    "created_after",
                    "modified_before",
                    "modified_after",
                    "search_method",
                    "name_weight",
                    "exact_name_weight",
                    "name_regexp_weight",
                    "tag_weight",
                    "similarity_threshold",
                ]
            ).issubset(set(prefixes))
        )

    @handle_exception
    async def test_async_search(self, query: str, url: str):
        print_fn(f"Testing async_search on: {url} with query:{query}")
        results = await async_search(query, url)

        self.assertEqual(results.status, StatusType.OK)
        print_fn(f"Received {len(results.paths)} results")
        for path in results.paths:
            print_fn(f" {path.uri}")

    @handle_exception
    async def test_paginated_search(self, query: str, url: str):
        num_results = 0
        max_results = 18
        batch_size = 6

        print_fn(f"Testing paginated_search on: {url} with query:{query}. batch_size={batch_size}")
        async for results in paginated_search(query, url, return_predictions=True, batch_size=batch_size):
            self.assertEqual(results.status, StatusType.OK)
            num_results += len(results.item_list)
            print_fn(f"Received {num_results}/{max_results} results")

            for item in results.item_list:
                self.assertIsInstance(item, SearchItem)
                # Currently there are no status values for individual items
                # assert item.status == StatusType.OK
                # OM-54668: item.image and embed will be empty strings for now, but None in the future.
                self.assertIsNone(item.image)
                self.assertIsNone(item.embed)
                # predictions is a list of dictionaries that look like this:
                # {'tag': 'pickle barrel', 'prob': 0.019276369363069534}
                self.assertIsNotNone(item.predictions)
                print_fn(f" {str(item.path.uri)}")

            if num_results >= max_results:
                break

    @handle_exception
    async def test_paginated_search_with_click(self, query: str, url: str):
        num_results = 0
        max_results = 18
        batch_size = 6

        print_fn(f"Testing paginated_search on: {url} with query:{query}. batch_size={batch_size}")
        async for results in paginated_search(query, url, return_predictions=True, batch_size=batch_size):
            self.assertEqual(results.status, StatusType.OK)
            num_results += len(results.item_list)
            print_fn(f"Received {num_results}/{max_results} results")

            for item in results.item_list:
                self.assertIsInstance(item, SearchItem)
                # Currently there are no status values for individual items
                # assert item.status == StatusType.OK
                # OM-54668: item.image and embed will be empty strings for now, but None in the future.
                self.assertIsNone(item.image)
                self.assertIsNone(item.embed)
                # predictions is a list of dictionaries that look like this:
                # {'tag': 'pickle barrel', 'prob': 0.019276369363069534}
                self.assertIsNotNone(item.predictions)
                print_fn(f" {str(item.path.uri)}")

            await telemetry_event_click(
                query=query,
                url=url,
                n=len(results.item_list),
                n_results_total=num_results,
                asset_id="1",
                asset_rank=2,
                click_order=3,
                time_to_present=0.1,
                time_to_click=1.0,
                query_time=0.1,
                search_request_id="some_id",
                telemetry_context=TELEMETRY_CONTEXT,
            )

            if num_results >= max_results:
                break

    @handle_exception
    async def test_connection_recreation(self, query: str, url: str):
        print_fn(f"Testing async_search on: {url} with query:{query}")
        results = await async_search(query, url)

        self.assertEqual(results.status, StatusType.OK)
        print_fn(f"Received {len(results.paths)} results")
        for path in results.paths:
            print_fn(f" {path.uri}")

        client: NGSearchClient = NGSearchClient.get_instance()
        print_fn(f"closing transport for {client._connections.keys()}")
        for host in client._connections:
            await client._connections[host].transport.close()
            with self.assertRaises(Exception):
                await client_ping(client._connections[host].transport)

        print_fn("repeating the query to make sure connection is recovered")
        results = await async_search(query, url)
        self.assertEqual(results.status, StatusType.OK)
        self.assertGreater(len(results.paths), 0)

    @handle_exception
    async def test_paginated_search_with_projections(self, query: str, url: str):
        num_results = 0
        max_results = 64
        batch_size = 32

        print_fn(f"Testing paginated_search on: {url} with query:{query}. batch_size={batch_size}")
        async for results in paginated_search(query, url, return_projections=True, batch_size=batch_size):
            self.assertEqual(results.status, StatusType.OK)
            num_results += len(results.item_list)
            print_fn(f"Received {num_results}/{max_results} results")

            for item in results.item_list:
                self.assertIsInstance(item, SearchItem)
                # Currently there are no status values for individual items
                # assert item.status == StatusType.OK
                # OM-54668: item.image and embed will be empty strings for now, but None in the future.
                self.assertIsNone(item.image)
                self.assertIsNone(item.embed)
                # projection is a list of floating values that is representation of the CLIP embedding in the lower dimensional space.
                self.assertIsNotNone(item.projection)
                print_fn(f" {str(item.path.uri)}")

            if num_results >= max_results:
                break

    @handle_exception
    async def test_get_embedding_hierarchy(self, query: str, url: str):
        batch_size = 32

        query = f"{query} max:{batch_size}"

        print_fn(f"Testing hierarchy retrieval on: {url} with query:{query}.")
        result = await get_embedding_hierarchy(query, url, return_images=True)

        self.assertEqual(result.status, StatusType.OK)
        clusters = json.loads(result.clusters)
        clusters: List[dict] = json.loads(result.clusters)
        samples = clusters["search_items"]
        hierarchy_nodes = json.loads(clusters["hierarchy_nodes"])
        check_clusters(hierarchy_nodes=hierarchy_nodes)
        check_samples(samples=samples)

    @handle_exception
    async def test_telemetry_event_processed(self, query: str, url: str):
        response = await telemetry_event_results_presented(
            query=query,
            url=url,
            n=8,
            n_results_total=32,
            time_to_present=0.1,
            query_time=0.1,
            thumbnail_load_time=[1] * 32,
            search_request_id="some_id",
            telemetry_context=TELEMETRY_CONTEXT,
        )
        self.assertEqual(response.status, StatusType.OK)

    @handle_exception
    async def test_telemetry_event_clicked(self, query: str, url: str):
        response = await telemetry_event_click(
            query=query,
            url=url,
            n=8,
            n_results_total=32,
            asset_id="1",
            asset_rank=2,
            click_order=3,
            time_to_present=0.1,
            time_to_click=1.0,
            query_time=0.1,
            search_request_id="some_id",
            telemetry_context=TELEMETRY_CONTEXT,
        )
        self.assertEqual(response.status, StatusType.OK)


if __name__ == "__main__":

    async def tests():
        try:
            # # NOTE: Keep the commented out URLs just as examples for the test S3 bucket
            # # They are commented out for now, as DeepSearch is currentyl disable on that S3 bucket.
            for test_url in [
                "omniverse://rc-r15.ov.nvidia.com/Projects/DeepSearch",
                # "s3://deepsearch-test-bucket/Projects/DeepSearch",
                "s3://omniverse-content-production/Assets/Machinima/BannerlordII/Props",
                # "https://deepsearch-test-bucket.s3.eu-central-1.amazonaws.com/Projects/DeepSearch",
                "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Assets/Machinima/BannerlordII/Props",
            ]:
                await ManualCheck().run_all(test_url)

            await ManualCheck().run_multiserver(
                [
                    "omniverse://rc-r15.ov.nvidia.com/Projects/DeepSearch",
                    "s3://omniverse-content-production/Assets/Machinima/BannerlordII/Props",
                ]
            )

        except Exception as e:
            carb.log_error(f"Error running manual tests: {str(e)}")
            carb.log_error(f"{traceback.format_exc()}")
        finally:
            ManualCheck.print_test_stats()

        # app.shutdown()

    task = asyncio.ensure_future(tests())
