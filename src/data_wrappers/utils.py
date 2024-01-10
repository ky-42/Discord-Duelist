import asyncio
import functools
import inspect
import os
from typing import (
    Any,
    Awaitable,
    Callable,
    Concatenate,
    Dict,
    Optional,
    ParamSpec,
    Type,
    TypeVar,
)

import redis
import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client
from dotenv import load_dotenv


def is_main_instance(fn):
    """Decorator running function conditionally if this is the main bot isntantce.

    If MAIN_INSTANCE env variable is set to True the wrapped function will run if
    it is set to False the wrapped function will not run.

    Args:
        fn (function): Function to wrap and run conditionally.
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


# Generics for pipeline_watch decorator
LeftoverParameters = ParamSpec("LeftoverParameters")
ReturnType = TypeVar("ReturnType")


def pipeline_watch(
    redis_pool: redis_sync.Redis,
    watch_param_name: str,
    key_not_found_excepton: Type[Exception] = ValueError,
    max_retries: int = 5,
):
    """Sets up a redis pipeline and a redis watch command for some data.

    For watch to work you must switch the pipeline to mulit mode then call
    the execute method on the pipeline. This decorator does not do that for you.

    Args:
        redis_pool (redis_sync.Redis): Redis connection pool to use to create
            the pipeline.
        watch_param_name (str): Name of the parameter in the decorated function
            that will be passed the key to watch in the db. Example: "game_id"
            will watch the id passed to "game_id" when wrapped function is called.
        key_not_found_excepton (Type[Exception], optional): An exception to raise
            if the key from the watch_param_name parameter is not in the db.
            Defaults to ValueError.
        max_retries (int, optional): Number of time the wrapped function will
            rerun if a watch error occures. Defaults to 5.

        fn (Callable[ Concatenate[redis_async_client.Pipeline, LeftoverParameters], Awaitable[ReturnType], ]):
            Function to wrap that should be a coroutine that takes a redis pipeline
            as its first parameter.

    Raises:
        redis.WatchError: Raised if the key from the watch_param_name parameter
            is modified while the pipeline is being executed and the max number
            of retries has been exceded.
        key_not_found_excepton: Raised if the key from the watch_param_name
            parameter is not in the db.
        TypeError: Raised if the watch_param_name parameter is not in the
            decorated function.
    """

    def decorator(
        fn: Callable[
            Concatenate[redis_async_client.Pipeline, LeftoverParameters],
            Awaitable[ReturnType],
        ]
    ) -> Callable[LeftoverParameters, Awaitable[ReturnType]]:
        @functools.wraps(fn)
        async def wrapper(
            *args: LeftoverParameters.args, **kwargs: LeftoverParameters.kwargs
        ) -> ReturnType:
            # Gets signature of the wrapped function
            func_sig = inspect.signature(fn)

            # This works because the paramter we need to pass to will always be
            # the first one because of the type definition of this decorator.
            func_params = func_sig.bind(None, *args, **kwargs)

            # Makes sure the watch param exists
            if watch_param_name in func_params.arguments:
                watch_data = func_params.arguments[watch_param_name]

                async with redis_pool.pipeline() as pipe:
                    # Make sure game exists while operating on it and reruns
                    # function if watch error occurs.
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


class RedisDb:
    """Used for redis pubsub and basic other redis functions"""

    # Redis connection pool
    __pool = redis_sync.Redis(db=0)

    # Instance of pubsub task
    __pubsub_task: Optional[asyncio.Task] = None

    # Dict of channel patterns and their callbacks
    __pubsub_callbacks: Dict[str, Callable[[Any], Awaitable[None]]] = {}

    @staticmethod
    async def flush_db():
        """Clears whole redis instance"""
        await RedisDb.__pool.flushall()

    @staticmethod
    async def __recreate_pubsub_task() -> None:
        """Recreates pubsub task updating any callback changes"""

        if RedisDb.__pubsub_task != None:
            RedisDb.__pubsub_task.cancel()
        else:
            # Sets up expire events if its first time running
            await RedisDb.__pool.config_set("notify-keyspace-events", "Ex")

        new_pubsub_obj = RedisDb.__pool.pubsub()
        await new_pubsub_obj.psubscribe(**RedisDb.__pubsub_callbacks)
        RedisDb.__pubsub_task = asyncio.create_task(new_pubsub_obj.run())

    @staticmethod
    @is_main_instance
    def is_pubsub_callback(channel_pattern: str):
        """Decorator for adding a callback to be called when a pubsub event occurs.

        When a message is published to a channel that matches the channel_pattern
        parameter the decorated function will be called.

        Does not effect the decorated function in any way.

        If the callback of same name is already added then the function will
        overwrite old one.

        Args:
            channel_pattern (str): Pubsub channel pattern to listen to.

            fn (Callable[[Any], Awaitable[None]]): Callback function.
        """

        def wrapper(
            fn: Callable[[Any], Awaitable[None]]
        ) -> Callable[[Any], Awaitable[None]]:
            RedisDb.__pubsub_callbacks[channel_pattern] = fn

            # Adds pubsub task to event loop creating one if needed
            try:
                asyncio.get_running_loop().create_task(RedisDb.__recreate_pubsub_task())
            except:
                asyncio.new_event_loop().run_until_complete(
                    RedisDb.__recreate_pubsub_task()
                )

            return fn

        return wrapper

    @staticmethod
    @is_main_instance
    async def add_pubsub_callback(
        channel_pattern: str, callback_func: Callable[[Dict[str, str]], Awaitable[None]]
    ):
        """Manually add a pubsub callback.

        When a message is published to a channel that matches the channel_pattern
        function passed to callback_func will be ran.

        If the callback of same name is already added then the function will
        overwrite old one.

        Args:
            channel_pattern (str): Pubsub channel pattern to listen to.
            callback_func (Callable[[Dict[str, str]], Awaitable[None]]): Callback
                function.
        """

        RedisDb.__pubsub_callbacks[channel_pattern] = callback_func

        await RedisDb.__recreate_pubsub_task()

    @staticmethod
    @is_main_instance
    async def remove_pubsub_callback(channel_pattern: str):
        """Manually remove a pubsub callback.

        Args:
            channel_pattern (str): Pubsub channel pattern to remove callback for.

        Raises:
            KeyError: Raised if channel_pattern is not a registered pattern.
        """

        del RedisDb.__pubsub_callbacks[channel_pattern]

        await RedisDb.__recreate_pubsub_task()
