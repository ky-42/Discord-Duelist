import asyncio
import random
from dataclasses import asdict
from datetime import timedelta

import pytest
import redis

from exceptions.game_exceptions import ActiveGameNotFound
from exceptions.general_exceptions import PlayerNotFound

from . import GameStatus

test_state = GameStatus.Game(
    status=0,
    game="tic-tac-toe",
    bet=0,
    starting_player=1,
    player_names={"1": "player_one", "2": "player_two"},
    all_players=[1, 2],
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
        with pytest.raises(ActiveGameNotFound):
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

    async def test_player_confirm(self):
        sample = test_state

        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(sample))

        random_player = random.choice(sample.unconfirmed_players)

        remaining = await GameStatus.confirm_player(
            game_id=test_game_id, player_id=random_player
        )

        new_state = GameStatus.Game(**self.conn.json().get(test_game_id))

        assert (
            new_state.all_players == sample.all_players
            and new_state.unconfirmed_players != test_state.unconfirmed_players
        )

        sample.unconfirmed_players.remove(random_player)

        assert (
            remaining == sample.unconfirmed_players
            and new_state.unconfirmed_players == sample.unconfirmed_players
        )

    async def test_player_confirm_player_not_found(self):
        test_game_id = GameStatus._GameStatus__create_game_id()
        self.conn.json().set(test_game_id, ".", asdict(test_state))

        with pytest.raises(PlayerNotFound):
            await GameStatus.confirm_player(game_id=test_game_id, player_id=4)

    async def test_player_game_not_found(self):
        with pytest.raises(ActiveGameNotFound):
            await GameStatus.confirm_player(game_id="test", player_id=2)

    async def test_shadowkey_timeout(self):
        await GameStatus.start_expire_listener()

        callback_ran = False
        callback_id = "wrong"
        callback_state: GameStatus.Game | None = None

        async def shadowkey_callback(game_id: str, game_state: GameStatus.Game):
            nonlocal callback_ran
            callback_ran = True

            nonlocal callback_id
            callback_id = game_id

            nonlocal callback_state
            callback_state = game_state

        await GameStatus.add_expire_handler(shadowkey_callback)

        test_game_id = await GameStatus.add(test_state, timedelta(seconds=4))

        assert GameStatus.Game(**self.conn.json().get(test_game_id)) == test_state

        await asyncio.sleep(5)

        assert callback_ran

        assert self.conn.json().get(callback_id) == None
        assert callback_state == test_state

        assert (
            self.conn.json().get(GameStatus._GameStatus__get_shadow_key(test_game_id))
            == None
        )
