"""Contains the GameModuleLoading class which deals with game modules"""

from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Tuple, Type

from dotenv import load_dotenv

# Stops circular import
if TYPE_CHECKING:
    from game_modules.game_classes import GameModule

load_dotenv()


class GameModuleLoading:
    """Collection of static methods that handle loading of game modules.

    Used to check available games, load them, and unload them.
    """

    # How long a game module can be unused before it is unloaded
    __clear_time = timedelta(minutes=15)

    # Stores the loaded game classes and when they were last accessed
    __loaded_game_modules: dict[str, None | Tuple[Type[GameModule], datetime]] = {
        game_module_name: None
        for game_module_name in os.listdir(os.getenv("GAME_MODULES_DIR"))
    }

    @staticmethod
    def check_game_module_details(game_name: str, user_count: int) -> bool:
        """Checks if the passed details are valid for the game module.

        Args:
            game_name (str): Name of the game module to check details against.
            user_count (int): Number of users that want to play game.

        Returns:
            bool: Where the details are valid or not. True is valid.
        """

        details = GameModuleLoading.get_game_module(game_name).get_details()

        user_count_result = details.check_valid_user_count(user_count)

        return user_count_result

    @staticmethod
    def list_all_game_modules() -> list[str]:
        """Returns a list of all the possible game modules"""

        return list(GameModuleLoading.__loaded_game_modules.keys())

    @staticmethod
    def get_game_module(game_name: str) -> Type[GameModule]:
        """Gets the game module class from the game module name.

        Args:
            game_name (str): Name of the game module to get.

        Raises:
            KeyError: Raised if the game module is not found.
            AttributeError: Raised if the game module does not have a load function.

        Returns:
            Type[GameModule]: The game module class.
        """

        # Check if the game module is already loaded
        if (
            game_module := GameModuleLoading.__loaded_game_modules.get(game_name)
        ) != None:
            # Update the last accessed time
            GameModuleLoading.__loaded_game_modules[game_name] = (
                game_module[0],
                datetime.now(),
            )

            return game_module[0]
        return GameModuleLoading.__load_game_module(game_name)

    @staticmethod
    def __load_game_module(game_name: str) -> Type[GameModule]:
        """Loads a game module, adds it to loaded games and returns it"""

        try:
            game_module = importlib.import_module(
                f"{os.getenv('GAME_MODULES_IMPORT_PATH')}.{game_name}",
            )

        except ModuleNotFoundError:
            raise KeyError(f"{game_name} is not a game")

        try:
            game: Type[GameModule] = game_module.load()

        except AttributeError:
            raise AttributeError(
                f"Game module of name {game_name} does not have a load function"
            )

        else:
            # Store the module in the loaded games dict and returns game class
            GameModuleLoading.__loaded_game_modules[game_name] = (game, datetime.now())
            return game

    @staticmethod
    def refresh_games_list() -> None:
        """Refreshes the list of available games"""

        GameModuleLoading.__loaded_game_modules = {
            game_module_name: None
            for game_module_name in os.listdir(os.getenv("GAME_MODULES_DIR"))
        }

        # Invalidate the cache to ensure the new modules can be loaded later
        importlib.invalidate_caches()

    @staticmethod
    def clear_old_games_modules() -> None:
        """Clears loaded games that not been accessed recently"""

        for game_name, game_values in GameModuleLoading.__loaded_game_modules.items():
            if game_values != None:
                if game_values[1] + GameModuleLoading.__clear_time < datetime.now():
                    GameModuleLoading.__loaded_game_modules[game_name] = None
