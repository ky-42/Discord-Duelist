import asyncio
import random
from dataclasses import asdict
from datetime import timedelta

import pytest
import redis

from data_wrappers import GameStatus
from exceptions import GameNotFound, UserNotFound

test_state = GameStatus.Game(
    state=0,
    game_module_name="tic-tac-toe",
    starting_user=1,
    usernames={"1": "user_one", "2": "user_two"},
    all_users=[1, 2],
    pending_users=[2],
)


db_number = GameStatus._GameStatus__db_number  # type: ignore


class TestGameStatus:
    conn = redis.Redis(db=db_number)
    pytestmark = pytest.mark.asyncio

    @pytest.fixture(scope="class", autouse=True)
    def setup_delete_db(self):
        yield

        # After tests in this class clears db
        TestGameStatus.conn.flushdb()

    async def test_add(self):
        test_game_id = await GameStatus.add(test_state, timedelta(minutes=15))

        assert GameStatus.Game(**self.conn.json().get(test_game_id)) == test_state
        # Checks if shadow key was created
        assert (
            int(self.conn.get(GameStatus._GameStatus__get_shadow_key(test_game_id)))
            == -1
        )

    async def test_successful_get(self):
        # Creates game id and add test data to redis db
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        got_data: GameStatus.Game = await GameStatus.get(test_game_id)

        assert got_data == test_state

    async def test_unsuccessful_get(self):
        with pytest.raises(GameNotFound):
            await GameStatus.get("wrong")

    async def test_set_expire(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        await GameStatus.set_expiry(test_game_id, timedelta(seconds=0.1))

        assert GameStatus.Game(**self.conn.json().get(test_game_id)) == test_state

        await asyncio.sleep(0.2)

        assert GameStatus.Game(**self.conn.json().get(test_game_id)) == test_state

        assert (
            self.conn.json().get(GameStatus._GameStatus__get_shadow_key(test_game_id))
            == None
        )

    async def test_delete_game(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        await GameStatus.delete(test_game_id)

        assert self.conn.json().get(test_game_id) == None

    async def test_user_confirm(self):
        sample = test_state

        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(sample))

        random_user = random.choice(sample.pending_users)

        remaining = await GameStatus.user_accepted(
            game_id=test_game_id, user_id=random_user
        )

        new_state = GameStatus.Game(**self.conn.json().get(test_game_id))

        assert (
            new_state.all_users == sample.all_users
            and new_state.pending_users != test_state.pending_users
        )

        sample.pending_users.remove(random_user)

        assert (
            remaining == sample.pending_users
            and new_state.pending_users == sample.pending_users
        )

    async def test_user_confirm_user_not_found(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        with pytest.raises(UserNotFound):
            await GameStatus.user_accepted(game_id=test_game_id, user_id=4)

    async def test_user_game_not_found(self):
        with pytest.raises(GameNotFound):
            await GameStatus.user_accepted(game_id="test", user_id=2)

    async def test_shadowkey_timeout(self):
        callback_ran = False
        callback_id = "wrong"
        callback_state: GameStatus.Game | None = None

        @GameStatus.handle_game_expire
        async def shadowkey_callback(game_id: str, game_state: GameStatus.Game):
            nonlocal callback_ran
            callback_ran = True

            nonlocal callback_id
            callback_id = game_id

            nonlocal callback_state
            callback_state = game_state

        test_game_id = await GameStatus.add(test_state, timedelta(seconds=1))

        assert GameStatus.Game(**self.conn.json().get(test_game_id)) == test_state

        await asyncio.sleep(2)

        assert callback_ran

        assert self.conn.json().get(callback_id) == None
        assert callback_state == test_state

        assert (
            self.conn.json().get(GameStatus._GameStatus__get_shadow_key(test_game_id))
            == None
        )
