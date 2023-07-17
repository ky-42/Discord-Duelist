import discord
from dataclasses import dataclass
from exceptions.game_exceptions import ToManyPlayers, NotEnoughPlayers
import functools
import inspect
from data_wrappers import GameStatus, GameData, UserStatus
from data_types import GameId

@dataclass
class GameInfo:
    min_players: int
    max_players: int
    thumbnail_file_path: str 
    
    def check_player_count(self, player_count):
        if player_count < self.min_players and player_count > self.max_players:
            return False
        return True


def load_game_state(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_sig = inspect.signature(func)
        func_params = func_sig.bind(*args, **kwargs)
        print(args)
        if "game_id" in (args_dict := func_params.arguments):
            game_id = args_dict["game_id"]
            game_state = await GameStatus.get_game(game_id)
            return await func(*args, **kwargs, game_state=game_state)
        else:
            raise TypeError("Missing required parameter: game_id")
    return wrapper

def load_game_data(data_class):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            a = inspect.signature(func)
            andas = a.bind(*args, **kwargs)
            print(args)
            if "game_id" in (args_dict := andas.arguments):
                game_id = args_dict["game_id"]
                game_data = await GameData.retrive_data(game_id, data_class)
                return await func(*args, **kwargs, game_data=game_data)
            else:
                raise TypeError("Missing required parameter: game_id")
        return wrapper
    return decorator
        
class Game:
    @staticmethod
    async def start_game(interaction: discord.Interaction, game_state: GameStatus.GameState, game_data) -> None:
        pass

    @staticmethod
    async def reply(game_id: GameId, interaction: discord.Interaction, game_state: GameStatus.GameState, game_data) -> None:
        pass

def send_message():
    pass

def end_game(
    
):
    pass