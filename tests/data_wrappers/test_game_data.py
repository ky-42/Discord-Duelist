from dataclasses import asdict, dataclass

import pytest
import redis

from data_wrappers.game_data import GameData
from exceptions import GameNotFound
from tests.testing_data.data_generation import game_id

pytestmark = pytest.mark.asyncio(scope="module")

db_number = GameData._GameData__db_number  # type: ignore
conn = redis.Redis(db=db_number)


@dataclass
class DataClassInherited:
    test_str: str
    test_number: int


test_data = DataClassInherited("test", -1)


@pytest.fixture(scope="module", autouse=True)
def clear_db():
    yield

    # After tests in this class clears db
    conn.flushdb()


async def test_successful_retrive(game_id):
    conn.json().set(game_id, ".", asdict(test_data))

    fetched_data = await GameData.get(game_id, DataClassInherited)

    assert isinstance(fetched_data, DataClassInherited)

    assert fetched_data == test_data


async def test_unsuccessful_retrive(game_id):
    with pytest.raises(GameNotFound):
        await GameData.get(game_id, DataClassInherited)


async def test_store_data(game_id):
    await GameData.store(game_id, test_data)

    stored_data = conn.json().get(game_id)

    assert stored_data == asdict(test_data)


async def test_delete_data(game_id):
    conn.json().set(game_id, ".", asdict(test_data))

    await GameData.delete(game_id)

    assert conn.json().get(game_id) is None
