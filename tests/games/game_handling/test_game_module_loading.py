import functools
import os
import time
from datetime import timedelta

import pytest
from dotenv import load_dotenv

from game_modules.game_handling.game_module_loading import GameModuleLoading
from game_modules.utils import GameModule

load_dotenv()
game_modules_dir = os.getenv("GAME_MODULES_DIR")


class TestGameModuleLoading:
    @pytest.fixture(autouse=True)
    def clear_fake_game_module(self):
        """
        Makes sure that the fake game is deleted after tests
        """

        yield

        if game_modules_dir != None:
            if os.path.exists(os.path.join(game_modules_dir, "Fake Game")):
                os.rmdir(os.path.join(game_modules_dir, "Fake Game"))
        else:
            raise FileNotFoundError("GAME_MODULES_DIR env var not set")

    @staticmethod
    def create_fake_game_module(func):
        """
        Creates a fake game in the games dir and deletes it after the test
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if game_modules_dir != None:
                os.mkdir(os.path.join(game_modules_dir, "Fake Game"))
            else:
                raise FileNotFoundError("GAME_MODULES_DIR env var not set")

            func(*args, **kwargs)

            os.rmdir(os.path.join(game_modules_dir, "Fake Game"))

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

    def test_list_modules(self):
        assert os.listdir(game_modules_dir) == GameModuleLoading.list_all_game_modules()

    @create_fake_game_module
    def test_wrong_list_modules(self):
        assert os.listdir(game_modules_dir) != GameModuleLoading.list_all_game_modules()

    def test_get_known_module(self):
        loaded_module = GameModuleLoading.get_game_module("Tic Tac Toe")

        assert type(loaded_module) == type(GameModule)

    def test_get_unknown_module(self):
        with pytest.raises(KeyError):
            GameModuleLoading.get_game_module("Unknown Game")

    @create_fake_game_module
    def test_get_improper_module(self):
        with pytest.raises(AttributeError):
            GameModuleLoading.get_game_module("Fake Game")

    def test_check_right_module_details(self):
        assert GameModuleLoading.check_game_module_details("Tic Tac Toe", 2)

    def test_check_high_module_details(self):
        assert not GameModuleLoading.check_game_module_details("Tic Tac Toe", 3)

    def test_check_low_module_details(self):
        assert not GameModuleLoading.check_game_module_details("Tic Tac Toe", 1)

    @change_clear_time(timedelta(seconds=0.5))
    def tests_clear_modules(self):
        GameModuleLoading.get_game_module("Tic Tac Toe")

        time.sleep(1)

        GameModuleLoading.clear_old_games_modules()

        assert GameModuleLoading._GameLoading__loaded_games["Tic Tac Toe"] == None  # type: ignore
