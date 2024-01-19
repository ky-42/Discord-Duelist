import functools
import os
import time
from datetime import timedelta

import pytest
from dotenv import load_dotenv

from game_modules.game_classes import GameModule
from game_modules.game_module_loading import GameModuleLoading
from tests.testing_data.module_generation import (
    add_fake_game_module,
    add_test_game_module,
)

load_dotenv()
game_modules_dir = os.getenv("GAME_MODULES_DIR")


@pytest.fixture
def fake_game_module_load(add_fake_game_module):
    GameModuleLoading.refresh_games_list()

    yield add_fake_game_module

    GameModuleLoading.refresh_games_list()


def change_clear_time(time: timedelta):
    """Decorator for changing the clear time for the loaded games"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            old_time = GameModuleLoading._GameModuleLoading__clear_time  # type: ignore
            GameModuleLoading._GameModuleLoading__clear_time = time  # type: ignore
            func(*args, **kwargs)
            GameModuleLoading._GameModuleLoading__clear_time = old_time  # type: ignore

        return wrapper

    return decorator


def test_details_player_count(add_test_game_module):
    assert not GameModuleLoading.check_game_module_details(add_test_game_module, 1)
    assert GameModuleLoading.check_game_module_details(add_test_game_module, 2)
    assert not GameModuleLoading.check_game_module_details(add_test_game_module, 3)


def test_list_modules():
    """IMPORTANT: Relies on refresh_games_list() to work correctly"""
    GameModuleLoading.refresh_games_list()

    assert os.listdir(game_modules_dir) == GameModuleLoading.list_all_game_modules()


def test_get_known_module(add_test_game_module):
    loaded_module = GameModuleLoading.get_game_module(add_test_game_module)

    assert type(loaded_module) == type(GameModule)


def test_get_unknown_module():
    with pytest.raises(KeyError):
        GameModuleLoading.get_game_module("Unknown Game")


def test_get_improper_module(fake_game_module_load):
    with pytest.raises(AttributeError):
        GameModuleLoading.get_game_module(fake_game_module_load)


def test_refresh_modules(add_test_game_module):
    GameModuleLoading._GameModuleLoading__loaded_game_modules = {}  # type: ignore

    with pytest.raises(KeyError):
        assert GameModuleLoading._GameModuleLoading__loaded_game_modules[add_test_game_module]  # type: ignore

    GameModuleLoading.refresh_games_list()

    GameModuleLoading._GameModuleLoading__loaded_game_modules[add_test_game_module]  # type: ignore


@change_clear_time(timedelta(seconds=0.05))
def test_clear_modules(add_test_game_module):
    GameModuleLoading.get_game_module(add_test_game_module)

    GameModuleLoading.clear_old_games_modules()

    assert GameModuleLoading._GameModuleLoading__loaded_game_modules[add_test_game_module] != None  # type: ignore

    time.sleep(0.05)

    GameModuleLoading.clear_old_games_modules()

    assert GameModuleLoading._GameModuleLoading__loaded_game_modules[add_test_game_module] == None  # type: ignore
