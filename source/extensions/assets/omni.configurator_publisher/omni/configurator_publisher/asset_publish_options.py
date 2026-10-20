# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
class AssetPublishOptions:
    DEFAULT_ASSET_NAME = "product_configurator_base"

    def __init__(self):
        self.usd_file_path = None
        self.temp_folder_path = None
        self.output_zip_name = None
        self.optimizer_config_path = None
        self.optimizer_max_mean_error = None
        self.kit_application_path = None
        self.validator_enabled_categories = []
        self.validator_enabled_rules = []
