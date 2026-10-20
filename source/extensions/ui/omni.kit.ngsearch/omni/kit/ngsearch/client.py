# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List, Optional
from unittest.mock import Mock

import carb
import carb.tokens
import omni.client
import toml
from idl.connection.transport import Client, TransportError
from idl.connection.transport.http import HttpClient
from idl.connection.transport.ws import WebSocketClient
from omni.discovery import DiscoverySearch
from omni.ngsearch import NGSearchClient as IDLNGSearchClient
from omni.ngsearch.client import NGSearchService
from omni.ngsearch.data import (
    BatchedSearchItem,
    ClusteringConfig,
    EmbeddingHierarchy,
    HierarchicalClustering,
    ProjectionConfig,
    SearchConfig,
    SearchItem,
    SearchQuery2,
    SearchResult,
    StatusOnlyResponse,
    StatusType,
    TelemetryContext,
)
from websockets.exceptions import ConnectionClosedError

from .config import PRESET_S3_BUCKETS, NGSearchConfig
from .data import (
    AuthorizedHostWithURL,
    EmbeddingHierarchyClusters,
    EmbeddingHierarchyResponse,
    EmbeddingsWithScores,
    S3Config,
    SupportedStorageBackends,
    TransportConfig,
)
from .exceptions import HierarchyRetrievalUnavailable, S3DiscoveryError, UnknownS3Bucket
from .utils import LogLevel, timer

TIMER_LOG_LEVEL = LogLevel.info


async def client_ping(transport: Client):
    # pinging WS directly is around 100x faster, than using any of IDL methods
    if isinstance(transport, WebSocketClient):
        _ = await transport.ws.ping()
    elif isinstance(transport, HttpClient):
        # TODO: this need to be verified, but normally ping functionality is not required for HttpClient
        #   NGSearch is currently using WS Client, so this functionality will need to be updated if the
        #   underlying transport changes
        pass
    elif isinstance(transport, Mock):
        carb.log_warn("Mock transport is detected. Running tests?")
    else:
        raise NotImplementedError(
            f"Currently {transport} is not supported, please update the ping functionality for this transport"
        )


# class to allow keeping the transport alive and avoid locks
@asynccontextmanager
async def keep_alive_context(transport: Client, keep_alive: bool = True) -> AsyncIterator[NGSearchService]:
    """Create service context with a given transport. If transport connection is closed - recreated connection
    before returning the service.

    Args:
        transport (Client): transport for the service connection
        keep_alive (bool, optional): keep connection alive when the context closes. Defaults to True.

    Yields:
        AsyncIterator[NGSearchService]: NGSearch service instance
    """
    close_transport: bool = True
    service = NGSearchService(transport)
    try:
        # if transport is initilazized
        if service.transport.prepared:
            await client_ping(service.transport)
            close_transport = False
    except Exception as e:
        await service.transport.close()
        carb.log_warn(f"Connection Error - recreating transport: ({str(e)})")

    if close_transport:
        service = await service.__aenter__()

    try:
        yield service
    finally:
        # transport was created within the context and keep_alive is False - close transport on exit
        if close_transport and not keep_alive:
            await service.__aexit__()


class NGSearchClient:
    __instance = None

    def __init__(self) -> None:
        if NGSearchClient.__instance is not None:
            raise Exception("NGSearchClient is a singleton!")
        else:
            NGSearchClient.__instance = self

        # Cache auth tokens per host
        self._auth_tokens: Dict[str, str] = {}
        # Hold discovered connections here
        self._connections: Dict[str, NGSearchService] = {}
        # Keep track of which hosts have no NGSearch available, so we only warn once.
        self._warned: Dict[str, bool] = {}
        # prevent client from connecting in two spots at once (prefixes and search)
        self._transport_locks: Dict[str, asyncio.Lock] = {}
        # set bucket config to None in the beginning
        self._s3_buckets: Optional[Dict[str, S3Config]] = None

    @property
    def s3_buckets(self) -> Dict[str, S3Config]:
        if self._s3_buckets is None:
            # load .omniverse.toml config
            self._omniverse_config = self._load_config()
            # get list of pre-configured S3 buckets
            self._s3_buckets = self.get_s3_buckets_from_config()
            # add NV Public DeepSearch config
            bucket: S3Config
            for bucket in PRESET_S3_BUCKETS:
                bucket_host = omni.client.break_url(bucket.url).host
                self._s3_buckets[bucket_host] = bucket

        return self._s3_buckets

    @staticmethod
    def _load_config() -> Optional[dict]:
        """Read .omniverse.toml file and return None if it does not exist at the expected location."""
        global_config_path = carb.tokens.get_tokens_interface().resolve("${omni_global_config}")
        _omniverse_config_path = os.path.join(global_config_path, "omniverse.toml").replace("\\", "/")
        if os.path.exists(_omniverse_config_path):
            return toml.load(_omniverse_config_path)
        else:
            return None

    def get_s3_buckets_from_config(self) -> Dict[str, S3Config]:
        """Get a dictionary of S3 buckets with their configuration parameters from the omniverse config"""
        if self._omniverse_config is None or self._omniverse_config.get("s3") is None:
            return {}

        s3_buckets = {}
        for bucket_string, config in self._omniverse_config["s3"].items():
            bucket_url = f"https://{bucket_string}"
            s3_buckets[bucket_string] = S3Config(
                url=bucket_url,
                bucket_name=config["bucket"],
                region_name=config["region"],
            )
        return s3_buckets

    @asynccontextmanager
    async def connection_context(self, host: str, blocking: bool = False) -> AsyncIterator[NGSearchService]:
        service: NGSearchService
        if blocking:
            async with self._transport_locks[host]:
                async with NGSearchService(self._connections[host].transport) as service:
                    yield service
        else:
            async with keep_alive_context(self._connections[host].transport) as service:
                yield service

    async def is_available(self, url: str) -> bool:
        broken_url = omni.client.break_url(url)
        host = broken_url.host
        if host in self._connections:
            return True
        return await self._discovery_and_authorization(url)

    async def close_connection(self, url: str) -> None:
        broken_url = omni.client.break_url(url)
        host = broken_url.host
        if host in self._connections:
            await self._connections[host].transport.close()
            del self._connections[host]
            del self._auth_tokens[host]

    async def _discovery_and_authorization(self, url: str) -> bool:
        """Discover and authorize connection to the NGSearch service based on the input URL."""
        broken_url = omni.client.break_url(url)
        scheme = broken_url.scheme
        host = broken_url.host

        if scheme == SupportedStorageBackends.omniverse:
            return await self._discovery_and_authorization_nucleus(url)
        elif scheme == SupportedStorageBackends.s3:
            try:
                for bucket in self.s3_buckets.values():
                    if host in bucket.bucket_name:
                        return await self._discovery_and_authorization_s3(url, bucket=bucket)
                raise UnknownS3Bucket(f"{host} S3 bucket is missing from configuration")
            except (ConnectionError, TransportError, ConnectionClosedError) as exc_info:
                if host not in self._warned or not self._warned[host]:
                    carb.log_warn(f"Error discovering NGSearch on {host}: {str(exc_info)}")
                    self._warned[host] = True
                return False
        elif scheme == SupportedStorageBackends.https:
            if host in self.s3_buckets:
                try:
                    return await self._discovery_and_authorization_s3(url, bucket=self.s3_buckets[host])
                except (
                    ConnectionError,
                    TransportError,
                    ConnectionClosedError,
                ) as exc_info:
                    if host not in self._warned or not self._warned[host]:
                        carb.log_warn(f"Error discovering NGSearch on {host}: {str(exc_info)}")
                        self._warned[host] = True
                    return False
            else:
                raise NotImplementedError(
                    "Only S3 buckets are currently supported with https access"
                    f" and {host} is not part of the list of supported one"
                )
        else:
            raise NotImplementedError(f"URL Scheme: {scheme} is not supported")

    async def _discover_ngsearch_s3(
        self,
        bucket: S3Config,
        deployment: str = os.getenv("OMNI_DEPLOYMENT", "external"),
    ) -> TransportConfig:
        """Discover the service API using the configuration file stored in the bucket."""
        result, _, content = await omni.client.read_file_async(f"{bucket.url}/{NGSearchConfig().discovery_path}")
        if result != omni.client.Result.OK:
            raise S3DiscoveryError(result)

        registration_content = json.loads(memoryview(content).tobytes())

        if deployment != "external":
            carb.log_info(f"Discovering {deployment} deployment of ngsearch")

        for reg in registration_content["reg"]:
            if reg["name"] == deployment:
                return TransportConfig(
                    host=reg["transport"]["params"]["host"],
                    port=reg["transport"]["params"]["port"],
                )

        raise S3DiscoveryError(
            f"Unknown deployment: {deployment}. " f"Available: {[reg['name'] for reg in registration_content['reg']]}"
        )

    async def _discovery_and_authorization_s3(self, url: str, bucket: Optional[S3Config] = None) -> bool:
        """Discover and authorize connection to the NGSearch deployed for S3 bucket.
        If bucket is not provided, bucket name will be inferred from the host name of the URL.

        Depending on the bucket setup the services interface will either be discovered or
        extension will connect directly through provided direct URL.
        """
        host = omni.client.break_url(url).host
        # get bucket configuration
        if bucket is None:
            bucket = self.s3_buckets[host]
        transport_params: Optional[TransportConfig] = None

        if bucket is None:
            raise ValueError("S3 bucket is unset")

        if bucket.use_discovery:
            transport_params = await self._discover_ngsearch_s3(bucket)
        else:
            if bucket.deepsearch_url is None:
                raise S3DiscoveryError(
                    f"Discovery for {bucket.bucket_name} is switched off, but 'deepsearch_url' is not provided"
                )
            broken_url = omni.client.break_url(bucket.deepsearch_url)
            transport_params = TransportConfig(host=broken_url.host, port=broken_url.port)

        entry = await IDLNGSearchClient.get_service(host=transport_params["host"], port=transport_params["port"])

        self._connections[host] = entry
        self._warned[host] = False
        self._auth_tokens[host] = "no token"
        self._transport_locks[host] = asyncio.Lock()
        return True

    async def _discovery_and_authorization_nucleus(self, url: str) -> bool:
        """Discover the ngsearch service and get the auth_token from omni.client

        Args:
            url (str): omniverse url

        Returns:
            bool: True on success, False on failure
        """

        broken_url = omni.client.break_url(url)
        host = broken_url.host

        try:
            async with DiscoverySearch(host) as discovery:
                deployment = os.getenv("OMNI_DEPLOYMENT", "external")
                if deployment != "external":
                    carb.log_info(f"Discovering {deployment} deployment of ngsearch")

                # NOTE: In order to be able to work with the earlier version of DeepSearch
                # that did not have heirarchy computation it is required to adjust capability
                # setting that is requested to be present on the server side
                #
                # Below we require the following methods and their respective versions to be
                # available on the server side:
                #       * search_gen_2 at version 0
                #       * find2 at version 3
                #       * get_prefixes at version 0
                #       * get_embeddings at version 0

                entry = await discovery.find(
                    NGSearchService,
                    meta={"deployment": deployment},
                    capabilities=dict(search_gen_2=0, find2=3, get_prefixes=0, get_embeddings=0),
                )
                if not entry or not entry.transport:
                    carb.log_warn("Unable to discover the search service.")
                    return False

            # make sure server is connected
            result, server_info = await omni.client.get_server_info_async(url)

            # on connection error - throw a runtime warning
            if result != omni.client.Result.OK:
                raise RuntimeWarning(str(result))

            self._connections[host] = entry
            self._warned[host] = False
            self._auth_tokens[host] = server_info.auth_token
            self._transport_locks[host] = asyncio.Lock()

        except ConnectionError as e:
            if host not in self._warned or not self._warned[host]:
                carb.log_warn(f"Error discovering NGSearch on {host}: {str(e)}")
                self._warned[host] = True
            return False
        except asyncio.CancelledError:
            return False
        except Exception as e:
            raise RuntimeWarning(str(e))

        return True

    async def _authorize_host(self, url: str) -> Optional[str]:
        if not url:
            return None
        broken_url = omni.client.break_url(url)
        host = broken_url.host

        if host not in self._connections:
            if not await self._discovery_and_authorization(url):
                return None
        return host

    async def get_embeddings(self, queries: List[str], url: str) -> List[str]:
        """Returns the embeddings for the provided strings, or an empty list
        if deepsearch is not available.

        Args:
            queries (List[str]): List of query strings.
            url (str): Omniverse URL.

        Returns:
            List[str]: List of embeddings of the same length or empty.
        """
        host = await self._authorize_host(url)
        if not host:
            return []

        service: NGSearchService
        async with self.connection_context(host, blocking=False) as service:
            if not service:
                carb.log_error("Connection to NGSearch Service failed")
                # TODO: What might cause this and how do we recover?
                return []

            embeddings = []
            result = await service.get_embeddings(queries)
            if result.data:
                for data in result.data:
                    embeddings.append(data.data)
            return embeddings

    async def get_prefixes(self, url: str) -> List[str]:
        """Returns the supported search prefixes on the url or an empty list if ngsearch is not available.

        Args:
            url (str): The omniverse URL

        Returns:
            List[str]: List of supported prefixes.
        """
        host = await self._authorize_host(url)
        if not host:
            return []

        service: NGSearchService
        async with self.connection_context(host, blocking=False) as service:
            if not service:
                carb.log_error("Connection to NGSearch Service failed")
                # TODO: What might cause this and how do we recover?
                return []

            prefix_object = await service.get_prefixes()
            return prefix_object.prefixes

    async def find2(self, query: str, url: str, telemetry_context: Optional[TelemetryContext] = None) -> SearchResult:
        if len(query) == 0:
            return

        host = await self._authorize_host(url)
        if not host:
            return

        broken_url = omni.client.break_url(url)
        path = broken_url.path if broken_url.path else "/"

        service: NGSearchService
        async with self.connection_context(host, blocking=False) as service:
            if not service:
                carb.log_error("Search Service was not found")
                return

            return await service.find2(
                query={"name": query, "parent": path, "tags": [query]},
                token=self._auth_tokens[host],
                telemetry_context=telemetry_context,
            )

    async def search_gen_2(
        self,
        query: str,
        url: str,
        return_predictions: bool,
        return_images: bool,
        return_embeddings: bool,
        return_projections: bool,
        similarity_threshold: float,
        search_config: Optional[SearchConfig] = None,
        projection_config: Optional[ProjectionConfig] = None,
        batch_size: Optional[int] = None,
        telemetry_context: Optional[TelemetryContext] = None,
    ) -> AsyncIterator[BatchedSearchItem]:
        host = await self._authorize_host(url)
        if not host:
            return

        broken_url = omni.client.break_url(url)
        path = broken_url.path if broken_url.path else "/"

        search_query = SearchQuery2(query=query, parent=path)
        service: NGSearchService
        async with self.connection_context(host, blocking=False) as service:
            if not service:
                carb.log_error("Search Service was not found")
                return

            async for response in service.search_gen_2(
                query=search_query,
                token=self._auth_tokens[host],
                return_predictions=return_predictions,
                return_images=return_images,
                return_embeddings=return_embeddings,
                return_projections=return_projections,
                similarity_threshold=similarity_threshold,
                search_config=search_config,
                projection_config=projection_config,
                batch_size=batch_size,
                telemetry_context=telemetry_context,
            ):
                # is status of response is Ok - process items' URLs to make
                #  sure they are in correct format
                if response.status == StatusType.OK:
                    # replace URL with the valid prefix
                    item_list = []
                    for r in response.item_list:
                        if broken_url.scheme in list(SupportedStorageBackends):
                            r.url = f"{broken_url.scheme}://{host}{r.path.uri}"
                        else:
                            carb.log_warn(f"Unsupported URL scheme: {broken_url.scheme}")
                        item_list.append(r)

                    # update reponse list with the new list
                    response.item_list = item_list

                yield response

    async def get_embedding_hierarchy(
        self,
        query: str,
        url: str,
        return_predictions: bool,
        return_images: bool,
        return_embeddings: bool,
        return_projections: bool,
        similarity_threshold: float,
        search_config: SearchConfig,
        clustering_config: Optional[ClusteringConfig] = None,
        telemetry_context: Optional[TelemetryContext] = None,
    ) -> EmbeddingHierarchy:
        host = await self._authorize_host(url)
        if not host:
            return

        broken_url = omni.client.break_url(url)
        path = broken_url.path if broken_url.path else "/"

        search_query = SearchQuery2(query=query, parent=path)
        service: NGSearchService
        async with self.connection_context(host, blocking=False) as service:
            if not service:
                carb.log_error("Search Service was not found")
                return

            try:
                return await service.get_embedding_hierarchy(
                    search_query,
                    token=self._auth_tokens[host],
                    return_predictions=return_predictions,
                    return_images=return_images,
                    return_embeddings=return_embeddings,
                    return_projections=return_projections,
                    similarity_threshold=similarity_threshold,
                    search_config=search_config,
                    clustering_config=clustering_config,
                    telemetry_context=telemetry_context,
                )
            except TransportError as exc:
                raise HierarchyRetrievalUnavailable(f"{host}: {str(exc)}")
            except Exception as exc_info:
                carb.log_warn(f"Embedding Hierarchy retrieval exception on '{host}': {str(exc_info)}")
                return EmbeddingHierarchyResponse.construct(
                    status=StatusType.UnknownError,
                    clusters=EmbeddingHierarchyClusters(search_items=[], hierarchy_nodes=json.dumps("")),
                )

    def _process_get_embedding_result(
        self, clustering_result: Optional[EmbeddingHierarchy], url: str
    ) -> EmbeddingHierarchyResponse:
        if clustering_result is None:
            return EmbeddingHierarchyResponse.construct(
                status=StatusType.UnknownError,
                clusters=EmbeddingHierarchyClusters(search_items=[], hierarchy_nodes=json.dumps("")),
                search_request_id="",
            )

        broken_url = omni.client.break_url(url)
        clusters: dict
        if isinstance(clustering_result.clusters, dict):
            clusters = clustering_result.clusters
        else:
            clusters = json.loads(clustering_result.clusters)

        search_items: List[SearchItem] = []
        for r in clusters.get("search_items", []):
            if broken_url.scheme in list(SupportedStorageBackends):
                r["url"] = f"{broken_url.scheme}://{broken_url.host}{r['path']['uri']}"
            else:
                carb.log_warn(f"Unsupported URL scheme: {broken_url.scheme}")
            search_items.append(r)

        return EmbeddingHierarchyResponse.construct(
            status=clustering_result.status,
            clusters=EmbeddingHierarchyClusters(search_items=search_items, hierarchy_nodes=clusters["hierarchy_nodes"]),
            search_request_id=clustering_result.search_request_id,
        )

    async def get_embedding_hierarchy_multiserver(
        self,
        query: str,
        url_list: List[str],
        return_predictions: bool,
        return_images: bool,
        return_embeddings: bool,
        return_projections: bool,
        similarity_threshold: float,
        search_config: SearchConfig,
        clustering_config: Optional[ClusteringConfig] = None,
        telemetry_context: Optional[TelemetryContext] = None,
        batch_size: Optional[int] = None,
        skip_authorization: bool = False,
    ) -> Optional[EmbeddingHierarchyResponse]:
        # if there is only a single URL provided - return to using a single URL hierarchy retrieval method
        if len(url_list) == 1:
            return self._process_get_embedding_result(
                await self.get_embedding_hierarchy(
                    query=query,
                    url=url_list[0],
                    return_predictions=return_predictions,
                    return_images=return_images,
                    return_embeddings=return_embeddings,
                    return_projections=return_projections,
                    similarity_threshold=similarity_threshold,
                    search_config=search_config,
                    clustering_config=clustering_config,
                    telemetry_context=telemetry_context,
                ),
                url=url_list[0],
            )

        if not skip_authorization:
            hosts = await asyncio.gather(*[self._authorize_host(url) for url in url_list])
            authorized_hosts_with_urls: List[AuthorizedHostWithURL] = [
                AuthorizedHostWithURL(host=host, url=url) for host, url in zip(hosts, url_list) if host
            ]
        else:
            authorized_hosts_with_urls = [
                AuthorizedHostWithURL(host=omni.client.break_url(url).host, url=url) for url in url_list
            ]

        # if no hosts are authorized - exit directly
        if len(authorized_hosts_with_urls) == 0:
            return None

        # if only one host is authorized - use the single URL hierarchy retrieval method
        if len(authorized_hosts_with_urls) == 1:
            return self._process_get_embedding_result(
                await self.get_embedding_hierarchy(
                    query=query,
                    url=authorized_hosts_with_urls[0]["url"],
                    return_predictions=return_predictions,
                    return_images=return_images,
                    return_embeddings=return_embeddings,
                    return_projections=return_projections,
                    similarity_threshold=similarity_threshold,
                    search_config=search_config,
                    clustering_config=clustering_config,
                    telemetry_context=telemetry_context,
                ),
                url=authorized_hosts_with_urls[0]["url"],
            )

        # get all the search results from all the servers
        async def _search_task(host_with_url: AuthorizedHostWithURL, retry_count: int = 1) -> BatchedSearchItem:
            with timer(
                message=f"'{query}' search on {host_with_url['url']}",
                level=TIMER_LOG_LEVEL,
            ):
                try:
                    response: BatchedSearchItem = await self.search_gen_2(
                        query,
                        url=host_with_url["url"],
                        return_predictions=return_predictions,
                        return_images=return_images,
                        return_embeddings=True,
                        return_projections=False,
                        similarity_threshold=similarity_threshold,
                        search_config=search_config,
                        batch_size=batch_size,
                        projection_config=(
                            ProjectionConfig(method=clustering_config.projection_method)
                            if clustering_config is not None
                            else None
                        ),
                        telemetry_context=telemetry_context,
                    ).__anext__()
                except StopAsyncIteration:
                    response = BatchedSearchItem(
                        status=StatusType.OK,
                        item_list=[],
                        search_request_id="",
                    )
                except Exception as exc_info:
                    carb.log_warn(f"Search task failure on '{host_with_url['url']}': {exc_info}")
                    response = BatchedSearchItem(
                        status=StatusType.UnknownError,
                        item_list=[],
                        search_request_id="",
                    )
                if response.status == StatusType.TokenExpired:
                    result, auth_token = await omni.client.refresh_auth_token_async(host_with_url["url"])
                    if result != omni.client.Result.OK:
                        carb.log_error(f"Refresh token failed. Status: {result}")
                    elif retry_count > 0:
                        self._auth_tokens[host_with_url["host"]] = auth_token
                        response = await _search_task(host_with_url, retry_count=retry_count - 1)

            if response.status != StatusType.OK:
                carb.log_error(f"Search Service exception: {response.status} ({host_with_url['host']})")
            return response

        with timer(
            message=f"total time for '{query}' search on all servers",
            level=TIMER_LOG_LEVEL,
        ):
            responses: List[BatchedSearchItem] = await asyncio.gather(
                *[_search_task(host_with_url) for host_with_url in authorized_hosts_with_urls]
            )

        # if more that 1 URL is authorized
        search_items: List[SearchItem] = []
        first_available_host: Optional[str] = None
        error_status: Optional[StatusType] = StatusType.OK
        search_request_id: Optional[str] = None

        for r, host_with_url in zip(responses, authorized_hosts_with_urls):
            if r.status == StatusType.OK:
                # memorize some information regarding the server that has a successful response
                first_available_host = host_with_url["host"]
                search_request_id = r.search_request_id
                search_items.extend(r.item_list)
            elif r.status == StatusType.TokenExpired:
                error_status = StatusType.TokenExpired
                await self.close_connection(host_with_url["url"])
                # refresh access token for the search_dir server
                await omni.client.refresh_auth_token_async(host_with_url["url"])
            elif r.status == StatusType.UnknownError:
                error_status = StatusType.UnknownError
                await self.close_connection(host_with_url["url"])

        # if no search items are returned - return directly
        if len(search_items) == 0:
            return EmbeddingHierarchyResponse.construct(
                status=error_status,
                clusters=EmbeddingHierarchyClusters(search_items=[], hierarchy_nodes=json.dumps("")),
            )

        if batch_size is not None:
            # get top scored items
            search_items = sorted(search_items, key=lambda item: item.path.score, reverse=True)
            search_items = search_items[:batch_size]

        # get hierarchical clustering of all the embeddings
        embedding_with_scores = [
            EmbeddingsWithScores(embedding=json.loads(item.embed), score=item.path.score) for item in search_items
        ]
        with timer(
            message=f"hierarchical clustering for '{query}' on '{first_available_host}'",
            level=TIMER_LOG_LEVEL,
        ):
            if first_available_host is None:
                raise ValueError("available host is not set")
            # use first server for projection computation
            async with self.connection_context(first_available_host, blocking=False) as service:
                try:
                    res: HierarchicalClustering = await service.compute_hierarchical_clustering(
                        serialized_embeddings_with_scores=json.dumps(embedding_with_scores),
                        clustering_config=clustering_config,
                        telemetry_context=telemetry_context,
                        token=self._auth_tokens[first_available_host],
                    )
                except TransportError as exc:
                    raise HierarchyRetrievalUnavailable(f"{first_available_host}: {str(exc)}")
                except Exception as exc_info:
                    carb.log_warn(f"Hierarchical clustering exception on {first_available_host}: {exc_info}")
                    return EmbeddingHierarchyResponse.construct(
                        status=StatusType.UnknownError,
                        clusters=EmbeddingHierarchyClusters(search_items=[], hierarchy_nodes=json.dumps("")),
                    )

        return EmbeddingHierarchyResponse.construct(
            status=res.status,
            clusters=EmbeddingHierarchyClusters(search_items=search_items, hierarchy_nodes=res.hierarchy_nodes),
            search_request_id=search_request_id,
        )

    async def telemetry_event_click(
        self,
        query: str,
        url: str,
        n: int,
        n_results_total: int,
        asset_id: str,
        asset_rank: int,
        click_order: int,
        time_to_present: float,
        time_to_click: float,
        query_time: float,
        search_request_id: str,
        telemetry_context: TelemetryContext,
    ) -> Optional[StatusOnlyResponse]:
        host = await self._authorize_host(url)
        if not host:
            return None

        # check if transport is prepared - in this case connection to NGSearch server
        # has been established, so no need to open it again

        service: NGSearchService
        async with keep_alive_context(self._connections[host].transport) as service:
            if not service:
                carb.log_error("Search Service was not found")
                return None

            response: StatusOnlyResponse = await service.telemetry_event_click(
                query=query,
                token=self._auth_tokens[host],
                n=n,
                n_results_total=n_results_total,
                asset_id=asset_id,
                asset_rank=asset_rank,
                click_order=click_order,
                time_to_present=time_to_present,
                time_to_click=time_to_click,
                query_time=query_time,
                search_request_id=search_request_id,
                telemetry_context=telemetry_context,
            )

            if response.status != StatusType.OK:
                carb.log_warn(f"Not OK Telemetry event status: {response.status}")

            return response

    async def telemetry_event_results_presented(
        self,
        query: str,
        url: str,
        n: int,
        n_results_total: int,
        time_to_present: float,
        query_time: float,
        thumbnail_load_time: List[float],
        search_request_id: str,
        telemetry_context: TelemetryContext,
    ) -> Optional[StatusOnlyResponse]:
        host = await self._authorize_host(url)
        if not host:
            return None

        service: NGSearchService
        async with keep_alive_context(self._connections[host].transport) as service:
            if not service:
                carb.log_error("Search Service was not found")
                return None

            response: StatusOnlyResponse = await service.telemetry_event_results_presented(
                query=query,
                token=self._auth_tokens[host],
                n=n,
                n_results_total=n_results_total,
                time_to_present=time_to_present,
                query_time=query_time,
                thumbnail_load_time=thumbnail_load_time,
                search_request_id=search_request_id,
                telemetry_context=telemetry_context,
            )

            if response.status != StatusType.OK:
                carb.log_warn(f"Not OK Telemetry event status: {response.status}")

            return response

    @staticmethod
    def get_instance():
        if NGSearchClient.__instance is None:
            NGSearchClient()
        return NGSearchClient.__instance

    def __del__(self):
        NGSearchClient.__instance = None
