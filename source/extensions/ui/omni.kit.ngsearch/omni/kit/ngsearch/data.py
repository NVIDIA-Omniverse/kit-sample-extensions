from enum import Enum
from typing import List, Optional

import numpy as np
import pydantic
from omni.ngsearch.data import (
    BatchedSearchItem,
    ClusteringConfig,
    ClusteringMethod,
    Path,
    ProjectionConfig,
    ProjectionMethod,
    SearchConfig,
    SearchItem,
    SearchResult,
    SearchResultCursor,
    StatusType,
    TelemetryContext,
)
from typing_extensions import TypedDict


class AuthorizedHostWithURL(TypedDict):
    host: str
    url: str


class EmbeddingsWithScores(TypedDict):
    embedding: List[np.float32]
    score: np.float32


class EmbeddingHierarchyClusters(TypedDict):
    search_items: List[SearchItem]
    hierarchy_nodes: str


class EmbeddingHierarchyResponse(pydantic.BaseModel):
    version: Optional[int] = pydantic.Field(default=None, title="version of the response")
    status: StatusType = pydantic.Field(..., title="status of hierarchy retrieval operation")
    clusters: EmbeddingHierarchyClusters = pydantic.Field(..., title="dictionary with clusters")
    search_request_id: Optional[str] = pydantic.Field(default=None, title="search request ID")

    class Config:
        arbitrary_types_allowed = True


class TransportConfig(TypedDict):
    host: str
    port: int


class SupportedStorageBackends(str, Enum):
    omniverse = "omniverse"
    s3 = "s3"
    https = "https"


class S3Config(pydantic.BaseModel):
    url: str = pydantic.Field(..., title="HTTPs URL to the bucket")
    bucket_name: str = pydantic.Field(..., title="S3 bucket name")
    region_name: str = pydantic.Field(..., title="S3 region name")
    use_discovery: bool = pydantic.Field(
        default=True,
        title="Flag that NGSearch service discovery is available on the bucket",
    )
    deepsearch_url: Optional[str] = pydantic.Field(default=None, title="URL of NGSearch service for direct connection")


__all__ = [
    # data classes
    "BatchedSearchItem",
    "ClusteringConfig",
    "ClusteringMethod",
    "Path",
    "ProjectionConfig",
    "ProjectionMethod",
    "SearchConfig",
    "SearchItem",
    "SearchResult",
    "SearchResultCursor",
    "StatusType",
    "TelemetryContext",
    "AuthorizedHostWithURL",
    "EmbeddingsWithScores",
    "EmbeddingHierarchyClusters",
    "EmbeddingHierarchyResponse",
    "TransportConfig",
    "SupportedStorageBackends",
    "S3Config",
]
