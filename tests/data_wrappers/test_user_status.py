from dataclasses import asdict
from typing import List, cast

import pytest
import redis

from data_types import UserId
from data_wrappers import UserStatus
from tests.testing_data.data_generation import user_id

db_number = UserStatus._UserStatus__db_number  # type: ignore


conn = redis.Redis(db=db_number)
pytestmark = pytest.mark.asyncio(scope="module")

max_active = UserStatus._UserStatus__max_active_games  # type: ignore
max_queued = UserStatus._UserStatus__max_queued_games  # type: ignore


@pytest.fixture(scope="module", autouse=True)
def clear_db():
    yield

    # After tests in this class clears db
    conn.flushdb()


async def test_join_game(user_id):
    test_user = UserStatus.User.generate_fake(max_active - 1, 0)

    conn.json().set(user_id, ".", asdict(test_user))

    add_id = "test"
    add_id_two = "test2"

    assert await UserStatus.join_game(user_id, add_id)
    assert await UserStatus.join_game(user_id, add_id_two)

    result = UserStatus.User(**conn.json().get(user_id))

    assert result.queued_games == test_user.queued_games + [add_id_two]
    assert result.active_games == test_user.active_games + [add_id]


async def test_join_game_nonexistent_user(user_id):
    game_id = "test"

    assert await UserStatus.join_game(user_id, game_id)

    expected_user_state = UserStatus.User(
        active_games=[game_id], queued_games=[], notifications=[]
    )

    assert conn.json().get(user_id) == asdict(expected_user_state)


async def test_join_game_full(user_id):
    test_user = UserStatus.User.generate_fake(max_active, max_queued)

    conn.json().set(user_id, ".", asdict(test_user))

    assert not await UserStatus.join_game(user_id, "test")


async def test_get_status_existing_user(user_id):
    test_user = UserStatus.User.generate_fake(1, 0)

    conn.json().set(user_id, ".", asdict(test_user))

    assert await UserStatus.get(user_id) == test_user


async def test_get_status_nonexistent_user(user_id):
    assert await UserStatus.get(user_id) is None


async def test_check_users_are_ready_all_ready(user_id):
    users = {user_id + i: UserStatus.User.generate_fake(1, 0) for i in range(3)}

    for current_user_id, user_obj in users.items():
        conn.json().set(current_user_id, ".", asdict(user_obj))

    assert await UserStatus.check_users_are_ready(list(users.keys()), "0")


async def test_users_not_ready(user_id):
    users = {user_id + i: UserStatus.User.generate_fake(1, 0) for i in range(2)}
    users[user_id + 2] = UserStatus.User.generate_fake(
        max_active, 1, starting_game_id=1
    )

    for current_user_id, user_obj in users.items():
        conn.json().set(current_user_id, ".", asdict(user_obj))

    assert not await UserStatus.check_users_are_ready(list(users.keys()), "5")


async def test_add_notification(user_id):
    test_user = UserStatus.User.generate_fake(1, 0)

    conn.json().set(user_id, ".", asdict(test_user))

    await UserStatus.add_notification(user_id, "test")

    assert "test" in UserStatus.User(**conn.json().get(user_id)).notifications


async def test_add_existing_notification(user_id):
    test_user = UserStatus.User.generate_fake(1, 0, 1)

    conn.json().set(user_id, ".", asdict(test_user))

    await UserStatus.add_notification(user_id, "0")

    assert len(UserStatus.User(**conn.json().get(user_id)).notifications) == 1


async def test_remove_notification(user_id):
    test_user = UserStatus.User.generate_fake(1, 0, 1)

    conn.json().set(user_id, ".", asdict(test_user))

    assert await UserStatus.remove_notification(user_id, "0")

    assert len(UserStatus.User(**conn.json().get(user_id)).notifications) == 0


async def test_nonexistent_notification(user_id):
    test_user = UserStatus.User.generate_fake(1, 0, 1)

    conn.json().set(user_id, ".", asdict(test_user))

    assert not await UserStatus.remove_notification(user_id, "test")


async def test_set_notification_id(user_id):
    test_user = UserStatus.User.generate_fake(1, 0, 1)

    conn.json().set(user_id, ".", asdict(test_user))

    await UserStatus.set_notification_id(user_id, 1)

    assert UserStatus.User(**conn.json().get(user_id)).notification_id == 1


async def test_clear_game(user_id):
    user_count = 3

    users = {
        user_id
        + i: UserStatus.User.generate_fake(1, 0, starting_game_id=max_active - 1)
        for i in range(user_count - 1)
    }
    users[user_id + user_count - 1] = UserStatus.User.generate_fake(max_active, 1)
    users[user_id + user_count - 1].notifications = [f"{max_active-1}"]

    for current_user_id, user_obj in users.items():
        conn.json().set(current_user_id, ".", asdict(user_obj))

    (moved_up_games, removed_notifications) = await UserStatus.clear_game(
        cast(List[UserId], list(users.keys())), str(max_active - 1)
    )

    assert moved_up_games == set(f"{max_active}")
    assert removed_notifications == [user_id + user_count - 1]

    for i in range(user_count - 1):
        assert conn.json().get(i) is None

    result = UserStatus.User(**conn.json().get(user_id + user_count - 1))

    assert str(max_active) in result.active_games
    assert len(result.queued_games) == 0
    assert len(result.active_games) == max_active
