import importlib
from datetime import datetime
from .games import helpers

game_name_id = {
    "Tic Tac Toe": 1,
}

loaded_games = {
    1: {
        "game": importlib.import_module("games.1"),
        "last_use": datetime.now()
    }
}

#Todo add return type of details
#Todo maybe move some stuff into decorator
def get_game_details(game_name: str):
    #Checks if a given game name exists and returns in details
    if game_name in game_name_id:
        if (game_id := game_name_id[game_name]) in loaded_games:
            loaded_games[game_id]["last_use"] = datetime.now()
            return loaded_games[game_id]["game"].details
        load_game(game_id)
    else:
        return False

#Todo add return type of details
def load_game(id: int): 
    game = importlib.import_module(f"games.{id}")
    loaded_games[id] = {
        "game": game,
        "last_use": datetime.now()
    }
    return game.details
