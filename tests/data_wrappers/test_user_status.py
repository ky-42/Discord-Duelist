from dataclasses import asdict
from random import randint

import pytest
import redis

from data_wrappers import UserStatus
from exceptions import GameNotFound, PlayerNotFound

test_state_current_game = UserStatus.User(
    current_games=["test_game_id"], queued_games=[], notifications=[]
)

test_state_queued_games = UserStatus.User(
    current_games=["test_game_id", "a", "b", "c", "d", "e"],
    queued_games=["test_game_id_2"],
    notifications=[],
)

test_state_queued_game_first_id = UserStatus.User(
    current_games=["test_game_id_wrong", "a", "b", "c", "d", "e"],
    queued_games=["test_game_id"],
    notifications=[],
)

db_number = UserStatus._UserStatus__db_number  # type: ignore


class TestUserStatus:
    conn = redis.Redis(db=db_number)
    pytestmark = pytest.mark.asyncio

    @pytest.fixture(scope="class", autouse=True)
    def setup_delete_db(self):
        yield

        # After tests in this class clears db
        TestUserStatus.conn.flushdb()

    async def test_get_status_existing_user(self):
        """
        Tests if get_status returns the correct UserState for an existing user
        """
        user_id = randint(1, 100000)

        self.conn.json().set(user_id, ".", asdict(test_state_queued_games))

        result = await UserStatus.get(user_id)

        assert result == test_state_queued_games

    async def test_get_status_nonexistent_user(self):
        """
        Tests if get_status returns None for a nonexistent user
        """
        user_id = randint(1, 100000)

        result = await UserStatus.get(user_id)

        assert result is None

    async def test_join_game_full_user(self):
        """
        Tests if join_game adds a game to the queued_games list for an existing user
        """
        user_id = randint(1, 10000)

        self.conn.json().set(user_id, ".", asdict(test_state_queued_games))

        game_id = "test_game_id_3"

        await UserStatus.join_game(user_id, game_id)

        result = self.conn.json().get(user_id)

        result = UserStatus.User(**result)

        assert result.queued_games == test_state_queued_games.queued_games + [game_id]
        assert result.current_games == test_state_queued_games.current_games

    async def test_join_game_nonexistent_user(self):
        """
        Tests if join_game creates a new user with the provided game as the current game
        when the user does not exist
        """
        user_id = randint(1, 10000)
        game_id = "test_game_id_0"

        await UserStatus.join_game(user_id, game_id)

        result = self.conn.json().get(user_id)

        expected_user_state = UserStatus.User(
            current_games=["test_game_id_0"], queued_games=[], notifications=[]
        )

        assert result == asdict(expected_user_state)

    async def test_check_users_are_ready_all_ready(self):
        """
        Tests if check_users_are_ready returns True when all users are ready (current_game is None)
        """
        user_ids = [randint(1, 10000), randint(1, 10000)]
        for user_id in user_ids:
            user_state = UserStatus.User(
                current_games=["test_game_id_0"], queued_games=[], notifications=[]
            )
            self.conn.json().set(user_id, ".", asdict(user_state))

        result = await UserStatus.check_users_are_ready("test_game_id_0", user_ids)

        assert result is True

    async def test_check_users_are_ready_current_already_set(self):
        """
        Tests if check_users_are_ready returns True when at least one user already has
        current_game set to the provided game_id
        (current_game is not None)
        """
        user_ids = [randint(1, 10000), randint(1, 10000)]
        self.conn.json().set(user_ids[0], ".", asdict(test_state_current_game))
        user_state = UserStatus.User(
            current_games=["test_game_id"], queued_games=[], notifications=[]
        )
        self.conn.json().set(user_ids[1], ".", asdict(user_state))

        result = await UserStatus.check_users_are_ready("test_game_id", user_ids)

        assert result is True

    async def test_check_users_are_ready_not_ready(self):
        """
        Tests if check_users_are_ready returns False when at least one user is not ready
        (current_game is not None)
        """
        user_ids = [randint(1, 10000), randint(1, 10000)]
        self.conn.json().set(user_ids[0], ".", asdict(test_state_current_game))
        user_state = UserStatus.User(
            current_games=[], queued_games=[], notifications=[]
        )
        self.conn.json().set(user_ids[1], ".", asdict(user_state))

        result = await UserStatus.check_users_are_ready("wrong", user_ids)

        assert result is False

    async def test_check_users_are_ready_nonexistent_user(self):
        """
        Tests if check_users_are_ready returns True when at least one user does not exist
        """
        user_ids = [randint(1, 10000), randint(1, 10000), randint(1, 10000)]
        self.conn.json().set(user_ids[0], ".", asdict(test_state_current_game))
        user_state = UserStatus.User(
            current_games=[], queued_games=[], notifications=[]
        )
        self.conn.json().set(user_ids[2], ".", asdict(test_state_current_game))

        with pytest.raises(PlayerNotFound):
            await UserStatus.check_users_are_ready("test_game_id", user_ids)

    async def test_clear_game(self):
        """
        Tests if clear_game removes the game from the user's current_game and queued_games lists
        """
        game_id = "test_game_id"
        user_ids = [randint(1, 10000), randint(1, 10000)]

        self.conn.json().set(user_ids[0], ".", asdict(test_state_current_game))
        self.conn.json().set(user_ids[1], ".", asdict(test_state_queued_game_first_id))

        await UserStatus.clear_game(game_id, user_ids)

        assert self.conn.json().get(user_ids[0]) == None

        result = UserStatus.User(**self.conn.json().get(user_ids[1]))
        assert result.queued_games == []
        assert result.current_games[0] == "test_game_id_wrong"

    async def test_remove_current_game_no_queued(self):
        """
        Tests if remove_game removes the game from the user's current_game
        and deletes user when there are no queued games
        """
        user_id = randint(1, 10000)
        self.conn.json().set(user_id, ".", asdict(test_state_current_game))

        await UserStatus._UserStatus__remove_game("test_game_id", user_id)

        assert self.conn.json().get(user_id) == None

    async def test_remove_current_game_with_queued(self):
        """
        Tests if remove_game removes the game from the user's current_game and queued_games lists
        moves up a queued game to current_game
        """
        user_id = randint(1, 10000)
        self.conn.json().set(user_id, ".", asdict(test_state_queued_games))

        await UserStatus._UserStatus__remove_game("test_game_id", user_id)

        result = UserStatus.User(**self.conn.json().get(user_id))
        assert result.current_games[-1] == test_state_queued_games.queued_games[0]

    async def test_remove_game_existing_user_queued_game(self):
        """
        Tests if remove_game removes the game from the user's queued_games list
        when the user exists and the game is in the queued_games list
        """
        user_id = randint(1, 10000)
        self.conn.json().set(user_id, ".", asdict(test_state_queued_games))

        await UserStatus._UserStatus__remove_game("test_game_id_2", user_id)

        result = UserStatus.User(**self.conn.json().get(user_id))

        assert result.queued_games == []
        assert result.current_games == test_state_queued_games.current_games

    async def test_remove_nonexistent_game(self):
        """ "
        Tests if remove_game raises ActiveGameNotFound when the game is not in the
        user's current_game or queued_games
        """
        user_id = randint(1, 10000)
        self.conn.json().set(user_id, ".", asdict(test_state_queued_games))

        with pytest.raises(GameNotFound):
            await UserStatus._UserStatus__remove_game("abc", user_id)

    async def test_remove_game_nonexistent_user(self):
        """
        Tests if remove_game raises PlayerNotFound when the user does not exist
        """
        user_id = randint(1, 10000)

        with pytest.raises(ValueError):
            await UserStatus._UserStatus__remove_game("abc", user_id)
