import asyncio
from dataclasses import asdict
from datetime import timedelta

import pytest
import redis

from exceptions.game_exceptions import ActiveGameNotFound
from exceptions.general_exceptions import PlayerNotFound

from . import GameStatus

test_state = GameStatus.GameState(
    status=0,
    game="tic-tac-toe",
    bet=0,
    starting_player=1,
    player_names={"1": "player_one", "2": "player_two"},
    confirmed_players=[1],
    unconfirmed_players=[2],
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

    async def test_successful_get(self):
        """
        Tests if game data can be fetch successfully
        """

        # Creates game id and add test data to redis db
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        got_data: GameStatus.GameState = await GameStatus.get_game(test_game_id)

        assert got_data == test_state

    async def test_unsuccessful_get(self):
        with pytest.raises(ActiveGameNotFound):
            await GameStatus.get_game("wrong")

    async def test_basic_add(self):
        test_game_id = await GameStatus.add_game(test_state, timedelta(minutes=15))

        assert GameStatus.GameState(**self.conn.json().get(test_game_id)) == test_state

    async def test_shadowkey_timeout(self):
        callback_ran = False
        callback_id = "wrong"
        callback_state: GameStatus.GameState | None = None

        async def shadowkey_callback(game_id: str, game_state: GameStatus.GameState):
            nonlocal callback_ran
            callback_ran = True

            nonlocal callback_id
            callback_id = game_id

            nonlocal callback_state
            callback_state = game_state

        await GameStatus.add_expire_handler(shadowkey_callback)

        test_game_id = await GameStatus.add_game(test_state, timedelta(seconds=2))

        assert GameStatus.GameState(**self.conn.json().get(test_game_id)) == test_state

        await asyncio.sleep(5)

        assert self.conn.json().get(callback_id) == None
        assert callback_state == test_state

        assert (
            self.conn.json().get(GameStatus._GameStatus__get_shadow_key(test_game_id))
            == None
        )

        assert callback_ran

    async def test_extend_game(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))
        self.conn.expire(test_game_id, timedelta(seconds=1))

        assert GameStatus.GameState(**self.conn.json().get(test_game_id)) == test_state

        await GameStatus.set_game_expire(test_game_id, timedelta(seconds=0.4))

        assert GameStatus.GameState(**self.conn.json().get(test_game_id)) == test_state

        await asyncio.sleep(0.7)

        assert (
            self.conn.json().get(GameStatus._GameStatus__get_shadow_key(test_game_id))
            == None
        )

    async def test_delete_game(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        await GameStatus.delete_game(test_game_id)

        assert self.conn.json().get(test_game_id) == None

    async def test_player_confirm(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        remaining = await GameStatus.confirm_player(game_id=test_game_id, player_id=2)

        new_state = GameStatus.GameState(**self.conn.json().get(test_game_id))

        assert (
            new_state.confirmed_players == [1, 2]
            and new_state.confirmed_players != test_state.confirmed_players
            and remaining == []
        )

    async def test_player_confirm_player_not_found(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        with pytest.raises(PlayerNotFound):
            await GameStatus.confirm_player(game_id=test_game_id, player_id=4)

    async def test_player_game_not_found(self):
        with pytest.raises(ActiveGameNotFound):
            await GameStatus.confirm_player(game_id="test", player_id=2)

    async def test_set_game_queued(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        await GameStatus.set_game_queued(game_id=test_game_id)

        new_state = GameStatus.GameState(**self.conn.json().get(test_game_id))

        assert new_state.status == 1

    async def test_set_game_in_progress(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        await GameStatus.set_game_queued(game_id=test_game_id)
        await GameStatus.set_game_in_progress(game_id=test_game_id)

        new_state = GameStatus.GameState(**self.conn.json().get(test_game_id))

        assert new_state.status == 2
