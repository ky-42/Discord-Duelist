import random
import string
from dataclasses import asdict, dataclass

import pytest
import redis

from data_wrappers.game_data import GameData
from exceptions import GameNotFound

db_number = GameData._GameData__db_number  # type: ignore


@dataclass
class DataClassInherited:
    test_str: str
    test_number: int


test_data = DataClassInherited("test", -1)


class TestGameData:
    conn = redis.Redis(db=db_number)
    pytestmark = pytest.mark.asyncio

    @pytest.fixture(scope="class", autouse=True)
    def setup_delete_db(self):
        yield

        # After tests in this class clears db
        TestGameData.conn.flushdb()

    @pytest.fixture
    def game_id(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    async def test_successful_retrive(self, game_id):
        TestGameData.conn.json().set(game_id, ".", asdict(test_data))

        fetched_data = await GameData.get(game_id, DataClassInherited)

        assert isinstance(fetched_data, DataClassInherited)

        assert fetched_data == test_data

    async def test_unsuccessful_retrive(self, game_id):
        with pytest.raises(GameNotFound):
            await GameData.get(game_id, DataClassInherited)

    async def test_store_data(self, game_id):
        await GameData.store(game_id, test_data)

        stored_data = TestGameData.conn.json().get(game_id)

        assert stored_data == asdict(test_data)

    async def test_delete_data(self, game_id):
        TestGameData.conn.json().set(game_id, ".", asdict(test_data))

        await GameData.delete(game_id)
