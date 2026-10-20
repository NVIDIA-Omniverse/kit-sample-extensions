import traceback
from pathlib import PurePosixPath

import carb
import omni.client

__all__ = ["OmniClientWrapper"]


def _encode_content(content):
    if type(content) == str:
        payload = bytes(content.encode("utf-8"))
    elif type(content) != type(None):
        payload = bytes(content)
    else:
        payload = bytes()

    return payload


class OmniClientWrapper:
    @staticmethod
    async def exists(path):
        try:
            result, entry = await omni.client.stat_async(path)
            return result == omni.client.Result.OK
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
            return False

    @staticmethod
    def exists_sync(path):
        try:
            result, entry = omni.client.stat(path)
            return result == omni.client.Result.OK
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
            return False

    @staticmethod
    def parent(path: str) -> str:
        url = omni.client.break_url(path)
        path = str(PurePosixPath(url.path).parent)
        return omni.client.make_url(scheme=url.scheme, host=url.host, path=path)

    @staticmethod
    def writeable(path: str):
        result: omni.client.Result
        stat: omni.client.ListEntry
        result, stat = omni.client.stat(path)
        if result != omni.client.Result.OK:
            # path doesn't exist - check if parent folder is writeable
            path = OmniClientWrapper.parent(path)
            result, stat = omni.client.stat(path)
            if result != omni.client.Result.OK:
                return False
        return bool(stat.access & omni.client.AccessFlags.WRITE)

    @staticmethod
    async def writeable_async(path: str) -> bool:
        result: omni.client.Result  # typehint
        stat: omni.client.ListEntry  # typehint
        result, stat = await omni.client.stat_async(path)
        if result != omni.client.Result.OK:
            # Path doesn't exist - check if we can write to parent path.
            result, stat = await omni.client.stat_async(OmniClientWrapper.parent(path))
            if result != omni.client.Result.OK:
                # Parent path doesn't exist
                return False
        return bool(stat.access & omni.client.AccessFlags.WRITE)

    @staticmethod
    async def write(path: str, content):
        carb.log_info(f"Writing {path}...")
        try:
            result = await omni.client.write_file_async(path, _encode_content(content))
            if result != omni.client.Result.OK:
                carb.log_error(f"Cannot write {path}, error code: {result}.")
                return False
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
            return False
        finally:
            carb.log_info(f"Writing {path} done...")

        return True

    @staticmethod
    async def copy(src_path: str, dest_path: str):
        src_path = str(src_path).replace("\\", "/")
        dest_path = str(dest_path).replace("\\", "/")
        carb.log_info(f"Copying from {src_path} to {dest_path}...")
        try:
            result = await omni.client.copy_async(src_path, dest_path, omni.client.CopyBehavior.OVERWRITE)
            if result == omni.client.Result.ERROR_SOURCE_IS_DEST:
                carb.log_warn(f"Cannot copy from {src_path} to {dest_path}, error code: {result}.")
                return False
            elif result != omni.client.Result.OK:
                carb.log_error(f"Cannot copy from {src_path} to {dest_path}, error code: {result}.")
                return False
            else:
                return True
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
        finally:
            carb.log_info(f"Copying from {src_path} to {dest_path} done...")

        return False

    @staticmethod
    async def read(src_path: str):
        carb.log_info(f"Reading {src_path}...")
        try:
            result, version, content = await omni.client.read_file_async(src_path)
            if result == omni.client.Result.OK:
                return memoryview(content).tobytes()
            else:
                carb.log_error(f"Cannot read {src_path}, error code: {result}.")
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
        finally:
            carb.log_info(f"Reading {src_path} done...")

        return None

    @staticmethod
    async def create_folder(path):
        carb.log_info(f"Creating dir {path}...")
        result = await omni.client.create_folder_async(path)
        return result == omni.client.Result.OK or result == omni.client.Result.ERROR_ALREADY_EXISTS
