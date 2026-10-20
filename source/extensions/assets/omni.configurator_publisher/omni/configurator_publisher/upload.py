# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

#!/usr/bin/python
"""
Example script showing how to upload title build and create a title package via the command line.

Run the script by specifying at least the Application ID, the file to upload, and an access_token:
python upload_build.py d1392f8e-7fca-58c7-9c02-d5e3b45612a1 new_game_build.zip -k <access_token>

The access_token obtained in step-2 is supplied as a command-line parameter using the -k flag

For all available options, run python upload_build.py -h
"""

import logging
import os
from argparse import ArgumentParser
from configparser import ConfigParser
from typing import Any, Callable, Dict

from botocore.config import Config

try:  # pragma: no cover
    import requests
    from boto3.exceptions import S3UploadFailedError
    from boto3.s3.transfer import S3Transfer, TransferConfig
    from boto3.session import Session
    from botocore.exceptions import ClientError
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    print('This script requires "requests", "boto3" and "tqdm" to be installed.  These can be installed with:')
    print("pip install requests boto3 tqdm")
    exit(1)

DEFAULT_API_URL = "https://builds.developer.nvidiagrid.net/api/1"
DEFAULT_NUM_THREADS = 10

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def do_upload(
    upload_config: Dict, file_path: str, num_threads: int, callback: Callable[[Any], None] = None
):  # pragma: no cover
    session = Session(
        aws_access_key_id=upload_config["s3UploadCredentials"]["accessKeyId"],
        aws_secret_access_key=upload_config["s3UploadCredentials"]["secretAccessKey"],
        aws_session_token=upload_config["s3UploadCredentials"]["sessionToken"],
        region_name=upload_config["region"],
    )
    s3_client = session.client("s3", config=Config(s3={"use_accelerate_endpoint": True}))

    transfer_config = TransferConfig(max_concurrency=num_threads)
    s3_transfer = S3Transfer(client=s3_client, config=transfer_config)

    s3_transfer.upload_file(file_path, upload_config["bucket"], upload_config["objectKey"], callback=callback)


def upload_file(upload_config: Dict, file_path: str, file_size: int, num_threads: int, quiet: bool):  # pragma: no cover
    logger.info("Starting file upload...")
    progress_bar = tqdm(
        total=file_size, unit="B", unit_scale=True, unit_divisor=1024, smoothing=0.2, desc="Upload", disable=quiet
    )

    def upload_progress(chunk):
        progress_bar.update(chunk)

    do_upload(upload_config, file_path, num_threads, callback=upload_progress)

    progress_bar.close()
    logger.info(f"File upload complete.")


def create_build_entry(api_url, data, access_token):  # pragma: no cover
    logger.info(f"Creating build entry...")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    upload_config = None
    response_error = None
    response = requests.post(f"{api_url}/builds", headers=headers, json=data)
    try:
        upload_config = response.json()["_uploadConfig"]
    except Exception as error:
        print("error", error)
        response_error = response.text

    if upload_config:
        logger.debug(f"{response.text}")
        logger.info("Created build entry.")
        return True, upload_config
    else:
        return False, response_error
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    response = requests.post(f"{api_url}/builds", headers=headers, json=data)
    assert 201 == response.status_code, f"Failed to create a new build entry: {response.text}"
    return response.json()["_uploadConfig"]


if __name__ == "__main__":  # pragma: no cover
    try:
        parser = ArgumentParser()
        parser.add_argument(
            "app_id",
            **{
                "type": str,
                "action": "store",
                "help": "Application ID for the game that this build is to be associated to",
            },
        )
        parser.add_argument("file", **{"type": str, "action": "store", "help": "Path to the file to be uploaded"})
        parser.add_argument(
            "-t",
            "--target",
            **{
                "type": str,
                "action": "store",
                "help": "What NVIDIA service should receive the uploaded build",
                "choices": ["GEFORCENOW", "GAMEREADYSERVICES"],
                "default": "GEFORCENOW",
            },
        )
        parser.add_argument(
            "-l",
            "--launch_command",
            **{
                "type": str,
                "action": "store",
                "help": "Command required to launch the build, including any parameters or flags",
            },
        )
        parser.add_argument(
            "-k",
            "--key",
            **{"type": str, "action": "store", "help": "Access token to be used to perform the upload", "default": ""},
        )
        parser.add_argument(
            "-c",
            "--change_version",
            **{
                "type": str,
                "action": "store",
                "help": "Internal change version identifier; e.g., Git commit hash or Perforce CL number",
                "default": "",
            },
        )
        parser.add_argument(
            "-s",
            "--semantic_version",
            **{"type": str, "action": "store", "help": "External version identifier; e.g., 1.0.0", "default": ""},
        )
        parser.add_argument(
            "-r",
            "--release_date",
            **{
                "type": str,
                "action": "store",
                "help": "Scheduled date for the build to go live in GeForce NOW, in ISO-8601 format",
                "default": "",
            },
        )
        parser.add_argument(
            "-n",
            "--num_threads",
            **{
                "type": int,
                "action": "store",
                "help": "Number of threads to concurrently upload the file in chunks",
                "default": DEFAULT_NUM_THREADS,
            },
        )
        parser.add_argument(
            "-q",
            "--quiet",
            **{"dest": "quiet", "action": "store_true", "help": "Mutes most output for use in scripts/automation"},
        )
        parser.add_argument(
            "-d",
            "--debug",
            **{
                "dest": "debug",
                "action": "store_true",
                "help": "Outputs more verbose logging to assist with debugging/troubleshooting",
            },
        )
        parser.add_argument(
            "-u",
            "--url",
            **{"type": str, "action": "store", "help": "Base URL for the upload API", "default": DEFAULT_API_URL},
        )
        parser.add_argument(
            "-re",
            "--retry_count",
            **{"type": int, "action": "store", "help": "Amount of retries for upload", "default": 3},
        )
        options = parser.parse_args()

        if options.debug:
            logger.setLevel(logging.DEBUG)
        elif options.quiet:
            logger.setLevel(logging.ERROR)

        access_token = options.key

        if not access_token:
            raise RuntimeError("No Access token (key) found")

        file_path = options.file
        if not os.path.isfile(os.path.expanduser(file_path)):
            raise RuntimeError(f"Invalid file path specified: {file_path}")

        file_name = os.path.split(file_path)[1]
        file_size = os.stat(file_path).st_size

        data = {
            "appId": options.app_id,
            "fileDetails": {"fileName": file_name, "fileSize": file_size},
            "target": options.target,
        }

        if options.launch_command:
            data["launchCommand"] = options.launch_command
        if options.change_version:
            data["changeVersion"] = options.change_version
        if options.semantic_version:
            data["semanticVersion"] = options.semantic_version
        if options.release_date:
            data["scheduledRelease"] = options.release_date

        success, upload_config = create_build_entry(options.url, data, access_token)
        if not success:
            raise AssertionError(f"Failed to create a new build entry: {upload_config}")

        attempt = 1
        while True:
            try:
                upload_file(upload_config, file_path, file_size, options.num_threads, options.quiet)
                exit(0)
            except (ClientError, S3UploadFailedError) as ex:
                if attempt < options.retry_count:
                    logger.warning(f"Upload failed. (attempt {attempt}): {ex}")
                else:
                    logger.error(f"Error: {ex}")
                    raise RuntimeError(f"Upload Failed after {attempt} attempts ")
                attempt += 1
    except Exception as e:
        logger.error(f"Error: {e}")
        exit(1)
