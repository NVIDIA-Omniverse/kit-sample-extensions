# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from typing import AsyncIterator, List, Optional

import carb
from omni.ngsearch.data import (
    BatchedSearchItem,
    ClusteringConfig,
    EmbeddingHierarchy,
    ProjectionConfig,
    SearchConfig,
    SearchResult,
    StatusOnlyResponse,
    TelemetryContext,
)

from .client import NGSearchClient


async def is_available(url: str) -> bool:
    """Attempt discovery of NGSearch on the given url. Return true if successful.

    Args:
        url (str): omniverse url.

    Returns:
        bool: True if ngsearch is discoverable.
    """
    try:
        return await NGSearchClient.get_instance().is_available(url)
    except Exception as exc_info:
        carb.log_warn(f"NGSearch availability check exception on '{url}': {exc_info}")
        return False


async def close_connection(url: str) -> bool:
    """Close connection to NGSearch service.

    Args:
        url (str): omniverse url.
    """
    return await NGSearchClient.get_instance().close_connection(url)


async def async_search(query: str, url: str, telemetry_context: Optional[TelemetryContext] = None) -> SearchResult:
    """Search asynchronously as a generator.

    Example Usage:

    async for results in ngsearch.async_search(
        "red rusty barrel",
        "omniverse://test.ov.nvidia.com/",
        telemetry_context = TelemetryContext(
            app_name="create",
            app_version="1.2.3",
            ui_name="content_browser",
            ui_version="1.0.0",
            session_id="a823d92a-4ed3-4618-956e-0c560039b310",
        )
    ):
        for path in results:
            if path.type != "folder":
                print(f"{path.uri} is size {path.size}")

    Args:
        query (str): The ngsearch query.
        url (str): The omniverse url
        telemetry_context (Optional[TelemetryContext]): Telemetry Context -
            some information about the Client using NGSearch service

    Returns:
        SearchResult: A result with a status and list of result paths.
    """
    return await NGSearchClient.get_instance().find2(query=query, url=url, telemetry_context=telemetry_context)


async def paginated_search(
    query: str,
    url: str,
    return_predictions: Optional[bool] = None,
    return_images: Optional[bool] = None,
    return_embeddings: Optional[bool] = None,
    return_projections: Optional[bool] = None,
    similarity_threshold: Optional[float] = None,
    search_config: Optional[SearchConfig] = None,
    projection_config: Optional[ProjectionConfig] = None,
    batch_size: Optional[float] = None,
    telemetry_context: Optional[TelemetryContext] = None,
) -> AsyncIterator[BatchedSearchItem]:
    """Paginated Search returns the search results in pages of size batch_size, while also
    returning other potentially useful information:

        Predictions: A list of predicted tags with their probabilities.
        Images: base64 encoded thumbnail images of the search results.
        Embeddings: The CLIP embedding as a Pickled Numpy Array for the search results.

    Example Usage:

    async for results in ngsearch.paginated_search(
        "description:blue ext:usd",
        "omniverse://rc.ov.nvidia.com/Projects",
        return_embeddings=True,
        batch_size=30,
        telemetry_context = TelemetryContext(
            app_name="create",
            app_version="1.2.3",
            ui_name="content_browser",
            ui_version="1.0.0",
            session_id="a823d92a-4ed3-4618-956e-0c560039b310",
        )
    ):
        for result in results:
            ...

    Args:
        query (str): The search query.
        url (str): The omniverse url
        return_predictions (Optional[bool]): Return network prediction values. Defaults to None.
        return_images (Optional[bool]): Return result images encoded in base64. Defaults to None.
        return_embeddings (Optional[bool]): Return CLIP embeddings for results. Defaults to None.
        return_projections (Optional[bool]): Return projections of CLIP embeddings into a lower-dimensional space
            for results. Defaults to None.
        similarity_threshold (Optional[float]): Set similarity threshold. By default ngsearch does not filter by
            similarity.
        search_config (Optional[SearchConfig]): Choose between KNN (default) and ANN search. When selecting ANN, the
            candidates parameter can fine tune the results (higher values lead to more precise results)
        projection_config (Optional[ProjectionConfig]): Choose between different projection methods. Right now
            UMAP and PCA are supported. Defaults to None (which will result in UMAP projection method).
        batch_size (Optional[float]): Number of results per batch. Defaults to None.
        telemetry_context (Optional[TelemetryContext]): Telemetry Context -
            some information about the Client using NGSearch service

    Yields:
        AsyncIterator[BatchedSearchItem]: Check .status for errors, and .item_list for results. Each result contains the
        path, url and, depending on the arguments above, other information (image, embed, predictions).
    """
    async for result in NGSearchClient.get_instance().search_gen_2(
        query,
        url,
        return_predictions,
        return_images,
        return_embeddings,
        return_projections,
        similarity_threshold,
        search_config,
        projection_config,
        batch_size,
        telemetry_context=telemetry_context,
    ):
        yield result


async def get_embedding_hierarchy(
    query: str,
    url: str,
    return_predictions: Optional[bool] = None,
    return_images: Optional[bool] = None,
    return_embeddings: Optional[bool] = None,
    return_projections: Optional[bool] = None,
    similarity_threshold: Optional[float] = None,
    search_config: Optional[SearchConfig] = None,
    clustering_config: Optional[ClusteringConfig] = None,
    telemetry_context: Optional[TelemetryContext] = None,
) -> EmbeddingHierarchy:
    """Method that retrieves the clustering hierarchy from the server, while also
    returning other potentially useful information:

        Predictions: A list of predicted tags with their probabilities.
        Images: base64 encoded thumbnail images of the search results.
        Embeddings: The CLIP embedding as a Pickled Numpy Array for the search results.

    Example Usage:

    results = await ngsearch.get_embedding_hierarchy(
        "description:blue ext:usd",
        "omniverse://rc.ov.nvidia.com/Projects",
        return_embeddings=True,
        telemetry_context = TelemetryContext(
            app_name="create",
            app_version="1.2.3",
            ui_name="content_browser",
            ui_version="1.0.0",
            session_id="a823d92a-4ed3-4618-956e-0c560039b310",
        )
    ):

    Args:
        query (str): The search query.
        url (str): The omniverse url
        return_predictions (Optional[bool]): Return network prediction values. Defaults to None.
        return_images (Optional[bool]): Return result images encoded in base64. Defaults to None.
        return_embeddings (Optional[bool]): Return CLIP embeddings for results. Defaults to None.
        return_projections (Optional[bool]): Return projections of CLIP embeddings into a lower-dimensional space
            for results. Defaults to None.
        similarity_threshold (Optional[float]): Set similarity threshold. By default ngsearch does not filter by
            similarity.
        search_config (Optional[SearchConfig]): Choose between KNN (default) and ANN search. When selecting ANN, the
            candidates parameter can fine tune the results (higher values lead to more precise results)
        clustering_config (Optional[ClusteringConfig]): Choose between different projection and clustering methods.
            Right now UMAP and PCA are supported for projection computation and Circgrid for clustering.
            Defaults to None (which will result in UMAP projection method and Circgrid clustering).
        telemetry_context (Optional[TelemetryContext]): Telemetry Context -
            some information about the Client using NGSearch service

    Returns:
        EmbeddingHierarchy: Check .status for errors, and .clusters for the graph of clusters.
    """
    return await NGSearchClient.get_instance().get_embedding_hierarchy(
        query=query,
        url=url,
        return_predictions=return_predictions,
        return_images=return_images,
        return_embeddings=return_embeddings,
        return_projections=return_projections,
        similarity_threshold=similarity_threshold,
        search_config=search_config,
        clustering_config=clustering_config,
        telemetry_context=telemetry_context,
    )


async def get_embedding_hierarchy_multiserver(
    query: str,
    url_list: List[str],
    return_predictions: Optional[bool] = None,
    return_images: Optional[bool] = None,
    return_embeddings: Optional[bool] = None,
    return_projections: Optional[bool] = None,
    similarity_threshold: Optional[float] = None,
    search_config: Optional[SearchConfig] = None,
    clustering_config: Optional[ClusteringConfig] = None,
    telemetry_context: Optional[TelemetryContext] = None,
    batch_size: Optional[int] = None,
    skip_authorization: bool = False,
) -> Optional[EmbeddingHierarchy]:
    """Method that retrieves the clustering hierarchy from the server, while also
    returning other potentially useful information:

        Predictions: A list of predicted tags with their probabilities.
        Images: base64 encoded thumbnail images of the search results.
        Embeddings: The CLIP embedding as a Pickled Numpy Array for the search results.

    Example Usage:

    results = await ngsearch.get_embedding_hierarchy_multiserver(
        "description:blue ext:usd",
        [
            "omniverse://rc.ov.nvidia.com/Projects",
            "omniverse://content.ov.nvidia.com/Projects",
            "s3://omniverse-content-production/Assets/",
        ],
        return_embeddings=True,
        telemetry_context = TelemetryContext(
            app_name="create",
            app_version="1.2.3",
            ui_name="content_browser",
            ui_version="1.0.0",
            session_id="a823d92a-4ed3-4618-956e-0c560039b310",
        )
    ):

    Args:
        query (str): The search query.
        url_list (List[str]): List of backend URLs
        return_predictions (Optional[bool]): Return network prediction values. Defaults to None.
        return_images (Optional[bool]): Return result images encoded in base64. Defaults to None.
        return_embeddings (Optional[bool]): Return CLIP embeddings for results. Defaults to None.
        return_projections (Optional[bool]): Return projections of CLIP embeddings into a lower-dimensional space
            for results. Defaults to None.
        similarity_threshold (Optional[float]): Set similarity threshold. By default ngsearch does not filter by
            similarity.
        search_config (Optional[SearchConfig]): Choose between KNN (default) and ANN search. When selecting ANN, the
            candidates parameter can fine tune the results (higher values lead to more precise results)
        clustering_config (Optional[ClusteringConfig]): Choose between different projection and clustering methods.
            Right now UMAP and PCA are supported for projection computation and Circgrid for clustering.
            Defaults to None (which will result in UMAP projection method and Circgrid clustering).
        telemetry_context (Optional[TelemetryContext]): Telemetry Context -
            some information about the Client using NGSearch service
        batch_size (Optional[int]): number of samples to return
        skip_authorization (bool): if True - skip additional authorization check. Defaults to False.

    Returns:
        EmbeddingHierarchy: Check .status for errors, and .clusters for the graph of clusters.
    """
    return await NGSearchClient.get_instance().get_embedding_hierarchy_multiserver(
        query=query,
        url_list=url_list,
        return_predictions=return_predictions,
        return_images=return_images,
        return_embeddings=return_embeddings,
        return_projections=return_projections,
        similarity_threshold=similarity_threshold,
        search_config=search_config,
        clustering_config=clustering_config,
        telemetry_context=telemetry_context,
        batch_size=batch_size,
        skip_authorization=skip_authorization,
    )


async def get_prefixes(url: str) -> List[str]:
    """Returns the supported search prefixes on the url or an empty list if ngsearch is not available.

    Args:
        url (str): Omniverse URL

    Returns:
        List[str]: List of supported prefixes.
    """
    return await NGSearchClient.get_instance().get_prefixes(url)


async def get_embeddings(queries: List[str], url: str) -> List[str]:
    """Returns the embeddings for the provided strings, or an empty list if deepsearch is not available.

    The embeddings are pickled numpy arrays. In order to convert the embeddings into a numpy array:

    from omni.kit.ngsearch import get_embeddings
    import pickle
    import asyncio

    async def example():
        results = await get_embeddings(["red rusty barrel"], "omniverse://rc.ov.nvidia.com/")
        for result in results:
            arr = pickle.loads(result.encode('latin1'))
            print(arr)

    asyncio.ensure_future(example())

    Args:
        url (str): Omniverse URL
        queries (List[str]): List of string queries.

    Returns:
        List[str]: List of embeddings (or an empty list)
    """
    return await NGSearchClient.get_instance().get_embeddings(queries, url)


async def telemetry_event_click(
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
) -> StatusOnlyResponse:
    """Notification event that will tell the service that a certain asset was selected from the search result

    Example Usage:

    response = await ngsearch.telemetry_event_click(
        query="description:blue ext:usd",
        url="omniverse://rc.ov.nvidia.com/Projects",
        n = 8,
        n_results_total = 32,
        asset_id = 1,
        asset_rank = 2,
        click_order = 3,
        time_to_present = 0.1,
        time_to_click = 1.0,
        query_time = 0.1,
        search_request_id = "some_id",
        telemetry_context = TelemetryContext(
            app_name="create",
            app_version="1.2.3",
            ui_name="content_browser",
            ui_version="1.0.0",
            session_id="a823d92a-4ed3-4618-956e-0c560039b310",
        )
    )

    Args:
        query (str): The search query.
        url (str): The omniverse url
        n (int):  Number of paths requested
        n_results_total (int): n_results_total Total number of results returned up to click event
        asset_id (str): asset_id The ID of the asset on which user has clicked
        asset_rank (int): asset_rank The rank of the asset in search results
        click_order (int): click_order Order number of the click in a given search request; must start with 1
        time_to_present (float): Time in seconds between user initiating the search and the results being shown
        time_to_click (float): Time in seconds between showing results and clicking
        query_time (float): NGSearch response time in seconds
        search_request_id (str): search_request_id of the associated search request
        telemetry_context (TelemetryContext): Telemetry Context -
            some information about the Client using NGSearch service

    Returns:
        StatusOnlyResponse: Status for the telemetry info being set back to the server
    """

    return await NGSearchClient.get_instance().telemetry_event_click(
        query=query,
        url=url,
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


async def telemetry_event_results_presented(
    query: str,
    url: str,
    n: int,
    n_results_total: int,
    time_to_present: float,
    query_time: float,
    thumbnail_load_time: List[float],
    search_request_id: str,
    telemetry_context: TelemetryContext,
) -> StatusOnlyResponse:
    """Notification event that will tell the service that a certain asset was selected from the search result

    Example Usage:

    response = await ngsearch.telemetry_event_results_presented(
        query="description:blue ext:usd",
        url="omniverse://rc.ov.nvidia.com/Projects",
        n = 8,
        n_results_total = 32,
        time_to_present = 0.1,
        query_time = 0.1,
        thumbnail_load_time = [1] * 32,
        search_request_id = "some_id",
        telemetry_context = TelemetryContext(
            app_name="create",
            app_version="1.2.3",
            ui_name="content_browser",
            ui_version="1.0.0",
            session_id="a823d92a-4ed3-4618-956e-0c560039b310",
        )
    )

    Args:
        query (str): The search query.
        url (str): The omniverse url
        n (int):  Number of paths requested
        n_results_total (int): n_results_total Total number of results returned up to click event
        time_to_present (float): Time in seconds between user initiating the search and the results being shown
        query_time (float): NGSearch response time in seconds
        thumbnail_load_time (List[float]): Array of load times for individual thumbnails in seconds
        search_request_id (str): search_request_id of the associated search request
        telemetry_context (TelemetryContext): Telemetry Context -
            some information about the Client using NGSearch service

    Returns:
        StatusOnlyResponse: Status for the telemetry info being set back to the server
    """

    return await NGSearchClient.get_instance().telemetry_event_results_presented(
        query=query,
        url=url,
        n=n,
        n_results_total=n_results_total,
        time_to_present=time_to_present,
        query_time=query_time,
        thumbnail_load_time=thumbnail_load_time,
        search_request_id=search_request_id,
        telemetry_context=telemetry_context,
    )
