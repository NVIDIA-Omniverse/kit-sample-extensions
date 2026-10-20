import carb.settings
from pydantic import BaseConfig

from .data import S3Config


class NGSearchConfig(BaseConfig):
    nvidia_public_url_setting = "/exts/omni.kit.ngsearch/omniverse-content-production/deepsearch-url"
    # TODO: this is an internal URL of the DeepSearch service that server
    # NVIDIA public content and is only accessible inside NVIDIA network.
    # This default setting will be changed when a public instance of DeepSearch becomes available.
    nvidia_public_default_url = "ws://omniverse-content-production-internal.deepsearch.nvidia.com:80"
    discovery_path = ".omniverse/deepsearch/ngsearch-registration.json"

    class Config:
        env_prefix = "omni_kit_ngsearch_"


# set default settings
settings = carb.settings.get_settings()
settings.set_default(
    NGSearchConfig().nvidia_public_url_setting,
    NGSearchConfig().nvidia_public_default_url,
)

PRESET_S3_BUCKETS = [
    S3Config(
        url="https://omniverse-content-production.s3.us-west-2.amazonaws.com",
        bucket_name="omniverse-content-production",
        region_name="us-west-2",
        use_discovery=False,
        deepsearch_url=settings.get(NGSearchConfig().nvidia_public_url_setting),
    )
]
