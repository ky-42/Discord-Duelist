from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Tuple, Type

from dotenv import load_dotenv

from exceptions.game_exceptions import GameNotFound, NoLoadFunction

# Stops circular import
if TYPE_CHECKING:
    from games.utils import Game

load_dotenv()


class GameLoading:
    """
    Handles loading of game classes

    This class is a singleton and should not be initalized.
    It is used to get the available games and handles
    loading, unloading and checks for the games
    """

    __clear_time = timedelta(minutes=15)

    # Stores the loaded game classes and when they were last accessed
    __loaded_games: dict[str, None | Tuple[Type[Game], datetime]] = {
        game_name: None for game_name in os.listdir(os.getenv("GAMES_DIR"))
    }

    @staticmethod
    def check_game_details(game_name: str, player_count: int) -> bool:
        """
        Checks if the passed details are valid for the game

        Returns true if the details are valid and false if they are not
        """

        details = GameLoading.get_game(game_name).get_details()

        player_count_result = details.check_player_count(player_count)

        return player_count_result

    @staticmethod
    def list_all_games() -> list[str]:
        """
        Returns a list of all the possible games
        """

        return list(GameLoading.__loaded_games.keys())

    @staticmethod
    def get_game(game_name: str) -> Type[Game]:
        """
        Loads the game module if it isnt loaded already and returns the details
        Each moduel should have a details attribute which is a GameInfo object at the top level
        """

        try:
            if (game_module := GameLoading.__loaded_games.get(game_name)) != None:
                # Update the last accessed time
                GameLoading.__loaded_games[game_name] = (game_module[0], datetime.now())

                # Return 0 cause loaded games stores a tuple of (module, load_time)
                return game_module[0]
            return GameLoading.__load_game(game_name)

        except ModuleNotFoundError:
            raise GameNotFound(game_name)

    @staticmethod
    def __load_game(game_name: str) -> Type[Game]:
        """
        Loads a game module and gets the game class from it. It then
        adds the module to the loaded games dict and returns the game class
        """

        # Watch out any errors initalizing this are caught by the caller
        # so you won't see module errors
        game_module = importlib.import_module(f"games.game_modules.{game_name}")

        # Check if the module has a load function
        try:
            game: Type[Game] = game_module.load()

        except AttributeError:
            raise NoLoadFunction(game_name)

        else:
            # Store the module in the loaded games dict and returns game class
            GameLoading.__loaded_games[game_name] = (game, datetime.now())
            return game

    @staticmethod
    def clear_old_games():
        """
        Goes through all the games in the game dict and clears the
        ones which have not been access for any reason recently
        """

        for game_name, game_values in GameLoading.__loaded_games.items():
            if game_values != None:
                if game_values[1] + GameLoading.__clear_time < datetime.now():
                    GameLoading.__loaded_games[game_name] = None
