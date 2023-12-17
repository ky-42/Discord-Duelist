import asyncio
import functools
import inspect
import os
from typing import Any, Awaitable, Callable, Concatenate, Dict, ParamSpec, Type, TypeVar

import redis
import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client
from dotenv import load_dotenv

# Generic type for a function that takes a pipeline and some other parameters
P = ParamSpec("P")
R = TypeVar("R")


def pipeline_watch(
    redis_pool: redis_sync.Redis,
    watch_param_name: str,
    key_not_found_excepton: Type[Exception] = ValueError,
    max_retries: int = 5,
):
    """
    Decorator for setting a watch and pipeline on some data.

    IMPORTANT: To use this decorator the wrapped function must
    be asyncronous and accept an asyncronous redis pipeline as
    its first parameter

    When using the pipe if you do not call the execute() method
    there is no possibility of a watch error. Meaning to make sure
    data is not changed while you are operating on it you must
    call the execute() method on the pipeline.

    Parameters:
        redis_pool[redis_sync.Redis]:
            redis pool to use the operation

        watch_param_name[str]:
            name of the parameter in the decorated function to watch

        key_not_found_excepton[Optional[Exception]]:
            Exception to raise if key to watch is not found

        max_retries[int]:
            Amount of times the function will retry if a watch error occurs
    """

    def decorator(
        fn: Callable[Concatenate[redis_async_client.Pipeline, P], Awaitable[R]]
    ) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Gets signature of the wrapped function
            func_sig = inspect.signature(fn)

            # This works because the paramter we need to pass to will always be the first one
            # because of the type definition of this decorator
            func_params = func_sig.bind(None, *args, **kwargs)

            # Makes sure the watch param exists
            if watch_param_name in func_params.arguments:
                watch_data = func_params.arguments[watch_param_name]

                async with redis_pool.pipeline() as pipe:
                    # Make sure game exists while operating on it
                    # and reruns function till it completes without a watch error
                    while await redis_pool.exists(watch_data):
                        nonlocal max_retries

                        await pipe.watch(watch_data)
                        if max_retries > -1:
                            try:
                                return await fn(pipe, *args, **kwargs)
                            except redis.WatchError:
                                max_retries -= 1
                                continue
                        else:
                            raise redis.WatchError("Max retries reached")

                    raise key_not_found_excepton(
                        f"key {watch_param_name} not found in db"
                    )
            else:
                raise TypeError("Missing required parameter: " + watch_param_name)

        return wrapper

    return decorator


def is_main_instance(fn):
    """
    Checks the MAIN_INSTANCE environment variable to see if
    this instance of the bot is the main one.

    If True the wrapped function will run
    If False the wrapped function will not run
    """

    needs_await: bool = inspect.iscoroutinefunction(fn)

    async def async_wrapper(*args, **kwargs):
        load_dotenv()
        if os.getenv("MAIN_INSTANCE") == "True":
            return await fn(*args, **kwargs)

    def wrapper(*args, **kwargs):
        load_dotenv()
        if os.getenv("MAIN_INSTANCE") == "True":
            return fn(*args, **kwargs)

    if needs_await:
        return async_wrapper
    return wrapper


class RedisDb:
    """Used for general redis commands"""

    __pool = redis_sync.Redis(db=0)

    # Instance of pubsub task. Used to handle shadow key expire events
    __pubsub_task: asyncio.Task = asyncio.create_task(__pool.pubsub().run())

    __pubsub_callbacks: Dict[str, Callable[[Any], Awaitable[None]]]

    @staticmethod
    async def flush_db():
        await RedisDb.__pool.flushall()

    @staticmethod
    async def __recreate_pubsub_task():
        RedisDb.__pubsub_task.cancel()
        await RedisDb.__pubsub_task

        new_pubsub_obj = RedisDb.__pool.pubsub()
        await new_pubsub_obj.psubscribe(**RedisDb.__pubsub_callbacks)
        RedisDb.__pubsub_task = asyncio.create_task(new_pubsub_obj.run())

    @staticmethod
    @is_main_instance
    def is_pubsub_callback(channel_pattern: str):
        """
        Only one function can be registerd to a channel
        """

        def real_decorator(
            fn: Callable[[Any], Awaitable[None]]
        ) -> Callable[[Any], Awaitable[None]]:
            RedisDb.__pubsub_callbacks[channel_pattern] = fn

            asyncio.create_task(RedisDb.__recreate_pubsub_task())

            return fn

        return real_decorator

    @staticmethod
    @is_main_instance
    async def add_pubsub_callback(
        channel_pattern: str, fn: Callable[[Dict[str, str]], Awaitable[None]]
    ):
        """
        Only one function can be registerd to a channel
        """
        RedisDb.__pubsub_callbacks[channel_pattern] = fn

        await RedisDb.__recreate_pubsub_task()

    @staticmethod
    @is_main_instance
    async def remove_pubsub_callback(channel_pattern: str):
        del RedisDb.__pubsub_callbacks[channel_pattern]

        await RedisDb.__recreate_pubsub_task()
