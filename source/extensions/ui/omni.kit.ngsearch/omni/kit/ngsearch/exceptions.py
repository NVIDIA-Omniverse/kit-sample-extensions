class HierarchyRetrievalUnavailable(Exception):
    pass


class UnknownS3Bucket(ConnectionError):
    pass


class S3DiscoveryError(ConnectionError):
    pass
