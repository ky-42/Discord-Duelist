import asyncio
from typing import Tuple

import pytest
import pytest_asyncio
import pytest_mock
import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client

from data_wrappers.utils import RedisDb, is_main_instance, pipeline_watch

conn = redis_sync.Redis(db=15)
pytestmark = pytest.mark.asyncio(scope="module")


@pytest_asyncio.fixture(scope="module", autouse=True)
async def clear_db():
    yield

    # After tests in this class clears db
    await conn.flushdb()


async def test_is_main_instance(mocker: pytest_mock.MockFixture):
    async_ran = False
    normal_ran = False

    mocker.patch("os.getenv", return_value="False")

    @is_main_instance
    async def async_fn():
        nonlocal async_ran
        async_ran = True

    @is_main_instance
    def normal_fn():
        nonlocal normal_ran
        normal_ran = True

    await async_fn()
    normal_fn()

    assert not async_ran
    assert not normal_ran

    mocker.patch("os.getenv", return_value="True")

    await async_fn()
    normal_fn()

    assert async_ran
    assert normal_ran


class TestPipelineWatch:
    @pytest_asyncio.fixture(scope="module")
    async def test_data(self) -> Tuple[str, str]:
        """
        Fixture that adds test data to db

        returns Tuple[str, str]: key and value of test data added
        """

        await conn.set("test", "test")

        return ("test", "test")

    async def test_missing_param(self):
        @pipeline_watch(conn, "key")
        async def fn(pipe: redis_async_client.Pipeline):
            pass

        with pytest.raises(TypeError):
            await fn()

    async def test_key_not_found(self):
        class TestException(Exception):
            pass

        @pipeline_watch(conn, "key", TestException)
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            pass

        with pytest.raises(TestException):
            await fn("-1")

    async def test_watch_error_retry(self, test_data: Tuple[str, str]):
        run_count = 0

        @pipeline_watch(conn, "key")
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            nonlocal run_count
            run_count += 1

            if run_count == 1:
                await pipe.set(key, f"test")

            await pipe.execute()

        await fn(test_data[0])

        assert run_count == 2

    async def test_watch_error_max(self, test_data: Tuple[str, str]):
        """
        Makes sure the function retries when a watch error occurs but
        only up to the max_retries
        """

        run_count = 0

        @pipeline_watch(conn, "key", max_retries=2)
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            nonlocal run_count
            run_count += 1

            await pipe.set(key, f"test")

            await pipe.execute()

        with pytest.raises(redis_sync.WatchError):
            await fn(test_data[0])

        assert run_count == 3

    async def test_success(self, test_data: Tuple[str, str]):
        """
        Makes sure the function runs when no watch error occurs
        """

        run_count = 0

        @pipeline_watch(conn, "key")
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            nonlocal run_count
            run_count += 1

            pipe.multi()
            pipe.set(key, "testtwo")
            await pipe.execute()

        await fn(test_data[0])

        assert run_count == 1


class TestRedisDb:
    async def test_is_pubsub_callback(self):
        called = False
        value = None

        @RedisDb.is_pubsub_callback("test")
        async def fn(recived_value):
            nonlocal called
            called = True

            nonlocal value
            value = recived_value

        await asyncio.sleep(0.1)

        await conn.publish("test", "test")

        await asyncio.sleep(0.6)

        assert called

        assert value
        assert value["data"].decode("utf-8") == "test"

    async def test_manual_pubsub_add_remove(self):
        called = False
        value = None

        async def fn(recived_value):
            nonlocal called
            called = True

            nonlocal value
            value = recived_value

        await RedisDb.add_pubsub_callback("test", fn)

        await asyncio.sleep(0.1)

        await conn.publish("test", "test")

        await asyncio.sleep(0.6)

        assert called

        assert value
        assert value["data"].decode("utf-8") == "test"

        called = False
        value = None

        await RedisDb.remove_pubsub_callback("test")

        await asyncio.sleep(0.1)

        await conn.publish("test", "test")

        await asyncio.sleep(0.6)

        assert not called
        assert value is None
