import functools
import os
import time
from datetime import timedelta

import pytest
from dotenv import load_dotenv
from sqlalchemy import over

from games.game_handling.game_module_loading import GameModuleLoading
from games.utils import GameModule

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
                GameModuleLoading._GameLoading__clear_time = time  # type: ignore
                func(*args, **kwargs)
                GameModuleLoading._GameLoading__clear_time = timedelta(minutes=15)  # type: ignore

            return wrapper

        return decorator

    def test_list_games(self):
        assert os.listdir(games_dir) == GameModuleLoading.list_all_game_modules()

    @create_fake_game
    def test_wrong_list_games(self):
        assert os.listdir(games_dir) != GameModuleLoading.list_all_game_modules()

    def test_get_known_game(self):
        loaded_module = GameModuleLoading.get_game_module("Tic Tac Toe")

        assert type(loaded_module) == type(GameModule)

    def test_get_unknown_game(self):
        with pytest.raises(KeyError):
            GameModuleLoading.get_game_module("Unknown Game")

    @create_fake_game
    def test_get_improper_game(self):
        with pytest.raises(AttributeError):
            GameModuleLoading.get_game_module("Fake Game")

    def test_check_right_game_details(self):
        assert GameModuleLoading.check_game_module_details("Tic Tac Toe", 2)

    def test_check_high_game_details(self):
        assert not GameModuleLoading.check_game_module_details("Tic Tac Toe", 3)

    def test_check_low_game_details(self):
        assert not GameModuleLoading.check_game_module_details("Tic Tac Toe", 1)

    @change_clear_time(timedelta(seconds=0.5))
    def tests_clear_games(self):
        GameModuleLoading.get_game_module("Tic Tac Toe")

        time.sleep(1)

        GameModuleLoading.clear_old_games_modules()

        assert GameModuleLoading._GameLoading__loaded_games["Tic Tac Toe"] == None  # type: ignore
