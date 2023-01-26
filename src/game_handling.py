import importlib
import string
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
from exceptions import GameNotFound, PlayerNotFound


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

GameId = str


class GameStatus:
    def __init__(self, bot: Bot) -> None:
        self.pool = redis.Redis(db=1)
        self.bot = bot
    
    def get_game(self, game_id: GameId) -> GameState:
        if self.pool.exists(game_id):
            return GameState(**self.pool.json().get(game_id))
        raise GameNotFound
         
    def add_game(self, game_id: GameId, state: GameState):
        self.pool.json().set(game_id, '.', asdict(state))

    async def player_confirm(self, game_id: GameId, player_id: int):
        confirmed_player_index = self.pool.json().arrindex(game_id, '.unconfirmed_player', player_id)
        if confirmed_player_index:
            # TODO make into pipline as to batch commands
            self.pool.json().arrpop(game_id, '.unconfirmed_players', confirmed_player_index)
            self.pool.json().arrappend(game_id, '.confirmed_players', player_id)
            
            unconfirmed_list = self.pool.json().get(game_id, '.unconfirmed_players')
            
            if len(unconfirmed_list) == 0:
                self.bot.game_admin.start_game(game_id)

    

        
    
class GameAdmin:
    def __init__(self, bot: Bot):
        self.bot = bot

        self.loaded_games: dict[str, None | ModuleType] = {}

        for game_name in os.listdir("./games"):
            self.loaded_games[game_name] = None

    # ---------------------------------------------------------------------------- #
            
    def check_game_details(self, game_name: str, player_count: int) -> None:
        details = self.get_game_details(game_name)
        
        details.check_player_count(player_count)

    def get_game_details(self, game_name: str) -> GameInfo:
        if (game_module := self.loaded_games[game_name]) != None:
            return game_module.detail
        return self.__load_game(game_name).detail

    # Not to be called externally and only if the game isnt loaded already
    def __load_game(self, game_name:str) -> ModuleType:
        game = importlib.import_module(f"games.{game_name}")
        self.loaded_games[game_name] = game
        return game

    # ---------------------------------------------------------------------------- #

    async def initialize_game(
            self,
            game: str,
            bet: int,
            player_one: int,
            players: List[int]
        ):
        
        game_id = ''.join(random.choices(
            string.ascii_letters +
            string.digits,
            k = 16
        ))

        game_details = GameState(
            status = 0,
            game = game,
            bet = bet,
            ready_players = [],
            queued_players = [],
            confirmed_players = [player_one],
            unconfirmed_players = players
        )
        
        self.bot.game_status.add_game(game_id, game_details)
        
        await self.confirm_game(game_id)
    

    # ---------------------------------------------------------------------------- #

    async def confirm_game(self, game_id: GameId):
        unconfirmed_players = self.bot.game_status.get_game(game_id).unconfirmed_players

        for player_id in unconfirmed_players:
            await self.__send_confirm(player_id)
        
    async def __send_confirm(self, player_id: int):
        unconfimed_player = self.bot.get_user(player_id)
        
        if unconfimed_player:
            if not unconfimed_player.dm_channel:
                await unconfimed_player.create_dm()
            
            await unconfimed_player.dm_channel.send('hi')
        else:
            raise PlayerNotFound
    
    
    
    async def reject_game(self, game_id: GameId, rejecting_player: discord.User | discord.Member):
        pass

    # ---------------------------------------------------------------------------- #

    def start_game(self, game_id: GameId):
        pass

    def game_end(self):
        pass

    def cancel_game(self, game_id: GameId):
        pass
    
    # Run this when there is an error and a game need to be cleaned up when not initilized 
    # or half way through function
    def clear_game(self, game_id: GameId):
        pass


            
# class GameData:
#     def __init__(self):
#         pass
    

# class GameBase:
    
#     def play_move()
    
#     def get_game_data(key):
#         self.base_data['game_data'][key]
class GameConfirm(discord.ui.View):
    def __init__(self, bot: Bot, game_id: GameId):
        self.bot = bot
        self.game_id = game_id
        super().__init__()
    
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.game_status.player_confirm(self.game_id, interaction.user.id)
        await interaction.response.send_message('Game accepted!')



    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.game_status.reject_game(self.game_id, interaction.user)


