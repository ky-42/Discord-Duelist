import functools
import os
import time
from datetime import timedelta

import pytest
from dotenv import load_dotenv
from sqlalchemy import over

from games.game_handling.game_loading import GameLoading
from games.utils import Game

load_dotenv()
games_dir = os.getenv("GAMES_DIR")


class TestGameLoading:
    @pytest.fixture(autouse=True)
    def clear_fake_game(self):
        """
        Makes sure that the fake game is deleted after tests
        """

        yield

        if games_dir != None:
            if os.path.exists(os.path.join(games_dir, "Fake Game")):
                os.rmdir(os.path.join(games_dir, "Fake Game"))
        else:
            raise FileNotFoundError("GAMES_DIR env var not set")

    @staticmethod
    def create_fake_game(func):
        """
        Creates a fake game in the games dir and deletes it after the test
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if games_dir != None:
                os.mkdir(os.path.join(games_dir, "Fake Game"))
            else:
                raise FileNotFoundError("GAMES_DIR env var not set")

            func(*args, **kwargs)

            os.rmdir(os.path.join(games_dir, "Fake Game"))

        return wrapper

    @staticmethod
    def change_clear_time(time: timedelta):
        """
        Decorator for changing the clear time for the loaded games
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                GameLoading._GameLoading__clear_time = time  # type: ignore
                func(*args, **kwargs)
                GameLoading._GameLoading__clear_time = timedelta(minutes=15)  # type: ignore

            return wrapper

        return decorator

    def test_list_games(self):
        assert os.listdir(games_dir) == GameLoading.list_all_games()

    @create_fake_game
    def test_wrong_list_games(self):
        assert os.listdir(games_dir) != GameLoading.list_all_games()

    def test_get_known_game(self):
        loaded_module = GameLoading.get_game("Tic Tac Toe")

        assert type(loaded_module) == type(Game)

    def test_get_unknown_game(self):
        with pytest.raises(KeyError):
            GameLoading.get_game("Unknown Game")

    @create_fake_game
    def test_get_improper_game(self):
        with pytest.raises(AttributeError):
            GameLoading.get_game("Fake Game")

    def test_check_right_game_details(self):
        assert GameLoading.check_game_details("Tic Tac Toe", 2)

    def test_check_high_game_details(self):
        assert not GameLoading.check_game_details("Tic Tac Toe", 3)

    def test_check_low_game_details(self):
        assert not GameLoading.check_game_details("Tic Tac Toe", 1)

    @change_clear_time(timedelta(seconds=0.5))
    def tests_clear_games(self):
        GameLoading.get_game("Tic Tac Toe")

        time.sleep(1)

        GameLoading.clear_old_games()

        assert GameLoading._GameLoading__loaded_games["Tic Tac Toe"] == None  # type: ignore
