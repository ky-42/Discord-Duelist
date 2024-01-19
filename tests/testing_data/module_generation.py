"""Contains fixtures for creating testing modules

The fixtures put these modules in the game_modules directory for testing purposes.
They will be removed after the tests are done.
"""

import importlib
import os
import shutil

import pytest
from dotenv import load_dotenv

load_dotenv()
game_modules_dir = os.getenv("GAME_MODULES_DIR")


@pytest.fixture()
def add_fake_game_module():
    """Creates a game module folder that won't work"""

    if game_modules_dir != None:
        os.mkdir(os.path.join(game_modules_dir, "Fake Game"))
    else:
        raise FileNotFoundError("GAME_MODULES_DIR env var not set")

    importlib.invalidate_caches()

    yield "Fake Game"

    if game_modules_dir != None:
        os.rmdir(os.path.join(game_modules_dir, "Fake Game"))
    else:
        raise FileNotFoundError("GAME_MODULES_DIR env var not set")


@pytest.fixture()
def add_test_game_module():
    """Moves the Testing Game module to the game_modules directory"""

    current_dir = os.path.dirname(os.path.realpath(__file__))

    testing_game_folder_path = os.path.join(current_dir, "Testing_Game")

    if game_modules_dir != None:
        shutil.move(testing_game_folder_path, game_modules_dir)
    else:
        raise FileNotFoundError("GAME_MODULES_DIR env var not set")

    importlib.invalidate_caches()

    yield "Testing_Game"

    if game_modules_dir != None:
        shutil.move(
            os.path.join(game_modules_dir, "Testing Game"), testing_game_folder_path
        )
    else:
        raise FileNotFoundError("GAME_MODULES_DIR env var not set")
