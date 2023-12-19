from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Tuple, Type

from dotenv import load_dotenv

import exceptions

# Stops circular import
if TYPE_CHECKING:
    from games.utils import GameModule

load_dotenv()


class GameModuleLoading:
    """
    Handles loading of game modules

    This class is a singleton and should not be initalized.
    It is used to get the available games and handles
    loading, unloading and checks for the games
    """

    __clear_time = timedelta(minutes=15)

    # Stores the loaded game classes and when they were last accessed
    __loaded_game_modules: dict[str, None | Tuple[Type[GameModule], datetime]] = {
        game_module_name: None
        for game_module_name in os.listdir(os.getenv("GAMES_DIR"))
    }

    @staticmethod
    def check_game_module_details(game_name: str, player_count: int) -> bool:
        """
        Checks if the passed details are valid for the game module

        Returns true if the details are valid and false if they are not
        """

        details = GameModuleLoading.get_game_module(game_name).get_details()

        player_count_result = details.check_player_count(player_count)

        return player_count_result

    @staticmethod
    def list_all_game_modules() -> list[str]:
        """
        Returns a list of all the possible game modules
        """

        return list(GameModuleLoading.__loaded_game_modules.keys())

    @staticmethod
    def get_game_module(game_name: str) -> Type[GameModule]:
        """
        Loads the game module if it isnt loaded already and returns the details
        Each moduel should have a details attribute which is a GameInfo object at the top level

        Raises a KeyError if the game is not found
        """

        try:
            if (
                game_module := GameModuleLoading.__loaded_game_modules.get(game_name)
            ) != None:
                # Update the last accessed time
                GameModuleLoading.__loaded_game_modules[game_name] = (
                    game_module[0],
                    datetime.now(),
                )

                # Return 0 cause loaded games stores a tuple of (module, load_time)
                return game_module[0]
            return GameModuleLoading.__load_game_module(game_name)

        except ModuleNotFoundError:
            raise KeyError(f"{game_name} is not a game")

    @staticmethod
    def __load_game_module(game_name: str) -> Type[GameModule]:
        """
        Loads a game module and gets the game class from it. It then
        adds the module to the loaded games dict and returns the game class

        Raises a NotGame error if the module does not have a load function
        """

        # Watch out any errors initalizing this are caught by the caller
        # so you won't see module errors
        game_module = importlib.import_module(f"games.game_modules.{game_name}")

        # Check if the module has a load function
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
    def clear_old_games_modules():
        """
        Goes through all the games in the game dict and clears the
        ones which have not been access for any reason recently
        """

        for game_name, game_values in GameModuleLoading.__loaded_game_modules.items():
            if game_values != None:
                if game_values[1] + GameModuleLoading.__clear_time < datetime.now():
                    GameModuleLoading.__loaded_game_modules[game_name] = None
