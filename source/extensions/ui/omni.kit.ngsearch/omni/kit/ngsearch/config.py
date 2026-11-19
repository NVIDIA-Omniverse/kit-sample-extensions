import carb.settings
from pydantic import BaseConfig

from .data import S3Config


class NGSearchConfig(BaseConfig):
    nvidia_public_url_setting = "/exts/omni.kit.ngsearch/omniverse-content-production/deepsearch-url"
    # Configure the public content search endpoint explicitly when available.
    nvidia_public_default_url = ""
    discovery_path = ".omniverse/deepsearch/ngsearch-registration.json"

    class Config:
        env_prefix = "omni_kit_ngsearch_"


# set default settings
settings = carb.settings.get_settings()
settings.set_default(
    NGSearchConfig().nvidia_public_url_setting,
    NGSearchConfig().nvidia_public_default_url,
)

public_deepsearch_url = settings.get(NGSearchConfig().nvidia_public_url_setting)

PRESET_S3_BUCKETS = [
    S3Config(
        url="https://omniverse-content-production.s3.us-west-2.amazonaws.com",
        bucket_name="omniverse-content-production",
        region_name="us-west-2",
        use_discovery=False,
        deepsearch_url=public_deepsearch_url,
    )
] if public_deepsearch_url else []
