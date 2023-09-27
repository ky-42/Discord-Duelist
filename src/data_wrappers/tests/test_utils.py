from typing import Tuple

import pytest
import pytest_asyncio
import pytest_mock
import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client

from data_wrappers.utils import is_main_instance, pipeline_watch


class TestUtils:
    """
    Class holds test tests for the utils module

    These are functions that can be used by all api wrappers
    """

    conn = redis_sync.Redis(db=15)
    pytestmark = pytest.mark.asyncio

    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def setup_delete_db(self):
        yield

        # After tests in this class clears db
        await TestUtils.conn.flushdb()

    @pytest_asyncio.fixture(scope="class")
    async def test_data(self) -> Tuple[str, str]:
        """
        Fixture that adds test data to db

        returns Tuple[str, str]: key and value of test data added
        """

        await TestUtils.conn.set("test", "test")

        return ("test", "test")

    async def test_pipeline_missing_param(self):
        @pipeline_watch(TestUtils.conn, "key")
        async def fn(pipe: redis_async_client.Pipeline):
            pass

        with pytest.raises(TypeError):
            await fn()

    async def test_pipeline_key_not_found(self):
        class TestException(Exception):
            pass

        @pipeline_watch(TestUtils.conn, "key", TestException)
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            pass

        with pytest.raises(TestException):
            await fn("test")

    async def test_pipeline_watch_error_retry(self, test_data: Tuple[str, str]):
        """
        Makes sure the function retries when a watch error occurs
        """

        run_count = 0

        @pipeline_watch(TestUtils.conn, "key")
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            nonlocal run_count
            run_count += 1

            if run_count == 1:
                await pipe.set(key, f"test")

            await pipe.execute()

        await fn(test_data[0])

        assert run_count == 2

    async def test_pipeline_watch_error_max(self, test_data: Tuple[str, str]):
        """
        Makes sure the function retries when a watch error occurs but
        only up to the max_retries
        """

        run_count = 0

        @pipeline_watch(TestUtils.conn, "key", max_retries=2)
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            nonlocal run_count
            run_count += 1

            await pipe.set(key, f"test")

            await pipe.execute()

        with pytest.raises(redis_sync.WatchError):
            await fn(test_data[0])

        assert run_count == 3

    async def test_pipeline_watch_success(self, test_data: Tuple[str, str]):
        """
        Makes sure the function runs when no watch error occurs
        """

        run_count = 0

        @pipeline_watch(TestUtils.conn, "key")
        async def fn(pipe: redis_async_client.Pipeline, key: str):
            nonlocal run_count
            run_count += 1

            pipe.multi()
            pipe.set(key, "testtwo")
            await pipe.execute()

        await fn(test_data[0])

        assert run_count == 1

    async def test_is_main_instance(self, mocker: pytest_mock.MockFixture):
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
