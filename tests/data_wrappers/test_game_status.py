import asyncio
import random
from dataclasses import asdict
from datetime import timedelta

import pytest
import redis

from data_wrappers import GameStatus
from data_wrappers.utils import RedisDb
from exceptions import GameNotFound, UserNotFound
from tests.testing_data.data_generation import game_id

db_number = GameStatus._GameStatus__db_number  # type: ignore

conn = redis.Redis(db=db_number)
pytestmark = pytest.mark.asyncio(scope="module")

test_state = GameStatus.Game.generate_fake(
    state=0, game_module_name="Testing_Game", user_count=2, pending_user_count=1
)


@pytest.fixture(scope="module", autouse=True)
def clear_db():
    yield

    # After tests in this class clears db
    conn.flushdb()


async def test_add():
    test_game_id = await GameStatus.add(test_state, timedelta(minutes=15))

    assert GameStatus.Game(**conn.json().get(test_game_id)) == test_state
    # Checks if shadow key was created
    assert int(conn.get(GameStatus._GameStatus__get_shadow_key(test_game_id))) == -1


async def test_successful_get(game_id):
    # Creates game id and add test data to redis db
    conn.json().set(game_id, ".", asdict(test_state))

    got_data: GameStatus.Game = await GameStatus.get(game_id)

    assert got_data == test_state


async def test_unsuccessful_get():
    with pytest.raises(GameNotFound):
        await GameStatus.get("None")


async def test_set_expire(game_id):
    """If test fails try and increase timings in this test"""
    conn.set(game_id, -1)
    conn.set(GameStatus._GameStatus__get_shadow_key(game_id), -1)

    assert int(conn.get(GameStatus._GameStatus__get_shadow_key(game_id))) == -1

    await GameStatus.set_expiry(game_id, timedelta(seconds=1))

    await asyncio.sleep(1.1)

    assert conn.get(GameStatus._GameStatus__get_shadow_key(game_id)) is None


async def test_user_accepted(game_id):
    sample = GameStatus.Game.generate_fake(
        state=0, game_module_name="Testing_Game", user_count=3, pending_user_count=2
    )

    conn.json().set(game_id, ".", asdict(sample))

    random_user = random.choice(sample.pending_users)

    remaining = await GameStatus.user_accepted(game_id=game_id, user_id=random_user)

    new_state = GameStatus.Game(**conn.json().get(game_id))

    assert random_user not in new_state.pending_users
    assert random_user in new_state.all_users
    assert remaining == new_state.pending_users

    sample.pending_users.remove(random_user)

    assert sample.pending_users == remaining


async def test_user_confirm_user_not_found(game_id):
    conn.json().set(game_id, ".", asdict(test_state))

    with pytest.raises(UserNotFound):
        await GameStatus.user_accepted(game_id=game_id, user_id=4)


async def test_delete_game(game_id):
    conn.json().set(game_id, ".", asdict(test_state))

    await GameStatus.delete(game_id)

    assert conn.json().get(game_id) is None


async def test_shadowkey_timeout(game_id):
    """If test fails try and increase timings in this test"""

    callback_ran = False
    callback_id = "wrong"

    await RedisDb._RedisDb__create_pubsub_task()

    @GameStatus.handle_game_expire
    async def fn(game_id: str):
        nonlocal callback_ran
        callback_ran = True

        nonlocal callback_id
        callback_id = game_id

    conn.set(GameStatus._GameStatus__get_shadow_key(game_id), -1)
    conn.expire(GameStatus._GameStatus__get_shadow_key(game_id), timedelta(seconds=1))

    await asyncio.sleep(1.1)

    assert conn.json().get(callback_id) is None

    assert callback_ran
    assert callback_id == game_id

    assert conn.json().get(GameStatus._GameStatus__get_shadow_key(game_id)) is None
