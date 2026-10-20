# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from pathlib import Path

import aiohttp
import omni.kit.test
from omni.kit.converter.common.test_utils.utils import get_repo_root_path


class TestConverterStatus(omni.kit.test.AsyncTestCase):
    """Test suite for the Asset converter service status endpoints."""

    BASE_URL = "http://localhost:8011/convert/asset"
    TEST_DATA_PATH = Path(get_repo_root_path() / "test_data" / "asset-converter-service")

    async def test_health_endpoint(self):
        """Test the /health endpoint returns OK status."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/health") as resp:
                self.assertEqual(resp.status, 200)
                data = await resp.json()

                # Verify response structure
                self.assertIn("status", data)
                self.assertEqual(data["status"], "OK")

    async def test_ready_endpoint_when_idle(self):
        """Test the /ready endpoint returns ready status when no conversions are running."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/ready") as resp:
                self.assertEqual(resp.status, 200)
                data = await resp.json()

                # Verify response structure
                self.assertIn("ready", data)

                # Should be ready when idle
                self.assertIsInstance(data["ready"], bool)

    async def test_status_endpoint(self):
        """Test the /status endpoint returns detailed conversion state."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/status") as resp:
                self.assertEqual(resp.status, 200)
                data = await resp.json()

                # Verify all required fields are present
                self.assertIn("state", data)
                self.assertIn("active_jobs", data)
                self.assertIn("max_job_count", data)
                self.assertIn("available_slots", data)
                self.assertIn("current_jobs", data)

                # Verify field types
                self.assertIsInstance(data["state"], str)
                self.assertIsInstance(data["active_jobs"], int)
                self.assertIsInstance(data["max_job_count"], int)
                self.assertIsInstance(data["available_slots"], int)
                self.assertIsInstance(data["current_jobs"], list)

                # Verify state is one of the valid service states (IDLE or RUNNING only)
                self.assertIn(data["state"], ["IDLE", "RUNNING"])

    async def test_ready_and_status_consistency(self):
        """Test that /ready and /status endpoints return consistent information."""
        async with aiohttp.ClientSession() as session:
            # Get ready status
            async with session.get(f"{self.BASE_URL}/ready") as resp:
                self.assertEqual(resp.status, 200)
                ready_data = await resp.json()

            # Get detailed status
            async with session.get(f"{self.BASE_URL}/status") as resp:
                self.assertEqual(resp.status, 200)
                status_data = await resp.json()

            # If ready is True, there should be available slots
            if ready_data["ready"]:
                self.assertGreater(status_data["available_slots"], 0)

    async def test_exceed_max_concurrent_conversions(self):
        """Test that the 6th concurrent conversion is rejected with 503 when 5 are already running."""
        test_output_path = Path(omni.kit.test.get_test_output_path()) / "test_exceed_max"
        test_output_path.mkdir(parents=True, exist_ok=True)
        test_file = self.TEST_DATA_PATH / "cube.gltf"

        # Helper to start a conversion and track its response
        async def start_conversion(session, index):

            test_output_file = test_output_path / f"conversion_{index}.usd"
            job_body = {
                "import_path": test_file.as_posix(),
                "output_path": test_output_file.as_posix(),
                "converter_settings": {},
            }
            try:
                async with session.post(f"{self.BASE_URL}/process", json=job_body) as resp:
                    status = resp.status
                    data = await resp.json()
                    return index, status, data
            except Exception as e:
                return index, None, str(e)

        async with aiohttp.ClientSession() as session:
            all_tasks = [start_conversion(session, i) for i in range(15)]

            # Wait a brief moment to ensure they all start
            await asyncio.sleep(0.1)

            results = await asyncio.gather(*all_tasks, return_exceptions=True)

            # Analyze results
            accepted_count = 0
            rejected_count = 0

            for result in results:
                index, status, data = result
                if status == 200:
                    accepted_count += 1
                elif status == 503:
                    rejected_count += 1

            self.assertTrue(rejected_count > 0)
            self.assertTrue(accepted_count == 15 - rejected_count)
