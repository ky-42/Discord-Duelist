import importlib
import discord
import os
import random
from .main import Bot
from datetime import datetime
from typing import List
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from redis.commands.json.path import Path
from games.tests import GameInfo
from types import ModuleType


@dataclass
class GameState:
    # 0 = unconfirmed | 1 = confirmed but queued | 2 = in progress | 3 = finished
    status: int
    game: str
    bet: int
    ready_players: List[int]
    queued_players: List[int]
    confirmed_players: List[int]
    unconfirmed_players: List[int]

class GameNotFound(Exception):
    """Raised when game is not found in db"""

class PlayerNotFound(Exception):
    """Raised when looking for a player but they are not found"""

class GameStatus:
    def __init__(self, bot: Bot) -> None:
        self.pool = redis.Redis(db=1)
        self.bot = bot
    
    def get_game(self, game_id: int) -> GameState:
        if self.pool.exists(str(game_id)):
            return GameState(**self.pool.json().get(game_id))
        raise GameNotFound
         
    def add_game(self, game_id: int, state: GameState):
        self.pool.json().set(game_id, '.', asdict(state))
    
    async def send_confirms(self, game_id):
        unconfirmed_players = self.get_game(game_id).unconfirmed_players

        for player_id in unconfirmed_players:
            await self.__send_confirm(player_id)
        
    async def __send_confirm(self, player_id: int):
        player = self.bot.get_user(player_id)

        if player != None:
            if (dm_channel := player.dm_channel) != None:
                pass
            else:
                await player.create_dm()
        else:
            raise PlayerNotFound

        
    
class GameAdmin:
    def __init__(self, bot: Bot):
        self.bot = bot

        self.loaded_games: dict[str, None | ModuleType] = {}

        for game_name in os.listdir("./games"):
            self.loaded_games[game_name] = None
            
    # Not to be called externally and only if the game isnt loaded already
    def __load_game(self, game_name:str):
        game = importlib.import_module(f"games.{game_name}")
        self.loaded_games[game_name] = game
        return game

    def get_game_details(self, game_name: str):
        if (game_module := self.loaded_games[game_name]) != None:
            return game_module.detail
        return self.__load_game(game_name).detail

    def check_game_details(self, game_details: GameInfo):
    
    
    def initialize_game(
            self,
            game: str,
            bet: int,
            init_player: int,
            players: List[int]
        ):
        
        game_id = random.randint(1, 100000000)

        game_details = GameState(
            status = 0,
            game = game,
            bet = bet,
            ready_players = [],
            queued_players = [],
            confirmed_players = [init_player],
            unconfirmed_players = players
        )
        
        .add_game(game_id, game_details)
        
        self.confirm_game(game_id)
    
    def confirm_game(self, game_id: int):
        game_details = GameStatus.game_status_pool.get(game_id)
        
        for player_id in game_details.unconfirmed_players:
            unconfimed_player = bot.get_user(player_id)

    def cancel_game(self, game_id: int):
        pass

    def player_confim(self, player_id):
        pass

    
    def start_game(self):
        pass

    def game_end(self):
        pass


            
# class GameData:
#     def __init__(self):
#         pass
    

# class GameBase:
    
#     def play_move()
    
#     def get_game_data(key):
#         self.base_data['game_data'][key]
class GameConfirm(discord.ui.View):
    def __init__(self, game_id):
        super().__init__()

