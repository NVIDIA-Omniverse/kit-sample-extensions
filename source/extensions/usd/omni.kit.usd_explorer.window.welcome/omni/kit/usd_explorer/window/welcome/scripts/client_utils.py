import carb
import omni.client


def client_result_handler(func):  # pragma: no cover -- currently unused
    async def wrapped(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            if result != omni.client.Result.OK:
                carb.log_warn(f"Operation {func.__name__} with {args!r} failed, error code: {result}.")
                return False
            else:
                return True
        except Exception as e:
            carb.log_error(str(e))
            return False

    return wrapped


@client_result_handler
async def client_create(path, payload):  # pragma: no cover -- currently unused
    await omni.client.delete_async(path)
    return await omni.client.write_file_async(path, payload)


@client_result_handler
async def client_copy(src, dest):  # pragma: no cover -- currently unused
    return await omni.client.copy_async(src, dest, omni.client.CopyBehavior.OVERWRITE)


async def client_list(path):  # pragma: no cover -- currently unused
    try:
        result, entries = await omni.client.list_async(path)
        if result == omni.client.Result.OK:
            return entries
        else:
            carb.log_warn(f"Cannot list {path}, error code: {result}.")
            return None
    except Exception as e:
        carb.log_error(str(e))
        return None
