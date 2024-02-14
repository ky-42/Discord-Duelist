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

    # Move the Testing_Game folder to the game_modules directory
    if game_modules_dir != None:
        if os.path.exists(testing_game_folder_path):
            shutil.move(testing_game_folder_path, game_modules_dir)
        else:
            raise FileNotFoundError("Testing_Game folder not found")
    else:
        raise ValueError("GAME_MODULES_DIR env var not set")

    # Makes sure the module can be imported
    importlib.invalidate_caches()

    yield "Testing_Game"

    game_module_path = os.path.join(game_modules_dir, "Testing_Game")

    # Move the Testing_Game folder back to the testing_data directory
    if game_modules_dir != None:
        if os.path.exists(game_module_path):
            shutil.move(game_module_path, testing_game_folder_path)
        else:
            raise FileNotFoundError("Testing_Game folder not found")
    else:
        raise ValueError("GAME_MODULES_DIR env var not set")
