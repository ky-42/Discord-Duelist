import os
import importlib
from types import ModuleType
from exceptions.game_exceptions import GameNotFound

class GameLoading:
    # Stores the loaded game moduels
    loaded_games: dict[str, None | ModuleType] = {
        game_name: None for game_name in os.listdir("./games/game_modules")
    }

    # ---------------------------------------------------------------------------- #

    @staticmethod
    def check_game_details(game_name: str, player_count: int) -> None:
        details = GameLoading.get_game(game_name).details

        details.check_player_count(player_count)

    @staticmethod
    def get_game(game_name: str) -> ModuleType:
        """
        Loads the game module if it isnt loaded already and returns the details
        Each moduel should have a details attribute which is a GameInfo object at the top level
        """

        try:
            if (game_module := GameLoading.loaded_games.get(game_name)) != None:
                return game_module
            return GameLoading.__load_game(game_name)
        except:
            raise GameNotFound(game_name)

    # Not to be called externally and only if the game isnt loaded already
    @staticmethod
    def __load_game(game_name: str) -> ModuleType:
        # Watch out any errors initalizing this are caught by the caller
        # so you won't see module errors
        game = importlib.import_module(f"games.game_modules.{game_name}")
        GameLoading.loaded_games[game_name] = game
        return game
    
