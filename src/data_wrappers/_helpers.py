import functools
import inspect
from typing import Type

import redis
import redis.asyncio as redis_sync

from exceptions.game_exceptions import ActiveGameNotFound


def pipeline_watch(
    redis_pool: redis_sync.Redis,
    watch_param_name: str,
    value_not_found_excepton: Type[Exception] = ValueError,
):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if watch_param_name in (
                args_dict := inspect.getcallargs(func, *args, **kwargs)
            ):
                print(args_dict)
                watch_data = args_dict[watch_param_name]
                async with redis_pool.pipeline() as pipe:
                    await pipe.watch(watch_data)
                    # Make sure game exists while operating on it
                    while await pipe.exists(watch_data):
                        try:
                            return await func(*args, **kwargs, pipe=pipe)
                        except redis.WatchError:
                            continue
                    raise value_not_found_excepton(
                        f"Value of {watch_param_name} not found"
                    )
            else:
                raise TypeError("Missing required parameter: " + watch_param_name)

        return wrapper

    return decorator


def watch_helper(redis_pool: redis_sync.Redis, watch_param_name: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if watch_param_name in (
                args_dict := inspect.getcallargs(func, *args, **kwargs)
            ):
                watch_data = args_dict[watch_param_name]
                async with redis_pool.pipeline() as pipe:
                    await pipe.watch(watch_data)
                    # Make sure game exists while operating on it
                    while True:
                        try:
                            return await func(*args, **kwargs, pipe=pipe)
                        except redis.WatchError:
                            continue
            else:
                raise TypeError("Missing required parameter: " + watch_param_name)

        return wrapper

    return decorator
