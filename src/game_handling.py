import importlib
import string
import discord
import os
import random
from main import Bot
from typing import List, Mapping
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from games.tests import GameInfo
from types import ModuleType
from exceptions import GameNotFound, PlayerNotFound
from datetime import timedelta


@dataclass
class GameState:
    # 0 = unconfirmed | 1 = confirmed but queued | 2 = in progress | 3 = finished
    status: int
    game: str
    bet: int
    starting_player: int
    player_names: Mapping[int, str]
    queued_players: List[int]
    confirmed_players: List[int]
    unconfirmed_players: List[int]

GameId = str

class GameStatus:
    def __init__(self, bot: Bot) -> None:
        self.pool = redis.Redis(db=1)
        self.bot = bot
    
    async def get_game(self, game_id: GameId) -> GameState:
        if await self.pool.exists(game_id):
            return GameState(**await self.pool.json().get(game_id))
        raise GameNotFound
         
    async def add_game(self, game_id: GameId, state: GameState):
        await self.pool.json().set(game_id, '.', asdict(state))
        await self.pool.expire(game_id, timedelta(minutes=15))
    
    async def delete_game(self, game_id: GameId):
        await self.pool.delete(game_id)

    async def player_confirm(self, game_id: GameId, player_id: int) -> List[int]:
        async with self.pool.pipeline() as pipe:
            await pipe.watch(game_id)
            # Make sure game exists while operating on it
            while await pipe.exists(game_id):
                # Make sure player exists
                if ((index := await pipe.json().arrindex(game_id, '.unconfirmed_players', player_id)) != None):
                    try:
                        # Switch to buffered mode after watch
                        pipe.multi()
                        pipe.json().arrpop(game_id, '.unconfirmed_players', index)
                        pipe.json().arrappend(game_id, '.confirmed_players', player_id)
                        pipe.json().get(game_id, '.unconfirmed_players')
                        results = await pipe.execute()
                        
                        return results[2]

                    except redis.WatchError:
                        continue
                else:
                    raise PlayerNotFound(player_id)
            raise GameNotFound()
            
                                
            
        

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
        if (game_module := self.loaded_games.get(game_name)) != None:
            return game_module.details
        return self.__load_game(game_name).details

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
            player_ids: List[int],
            player_names: Mapping[int, str]
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
            starting_player = player_one,
            player_names = player_names,
            queued_players = [],
            confirmed_players = [player_one],
            unconfirmed_players = player_ids
        )
        
        # TODO make sure players have bet money
        
        await self.bot.game_status.add_game(game_id, game_details)
        
        await self.confirm_game(game_id, game_details)

    # ---------------------------------------------------------------------------- #
    
    async def confirm_game(self, game_id: GameId, game_state: GameState):
        for player_id in game_state.unconfirmed_players:
            await self.__send_confirm(player_id, game_id, game_state)
        
    async def __send_confirm(self, player_id: int, game_id: GameId, game_state: GameState):
        player_one = await self.bot.get_user(game_state.starting_player)
        
        dm = await self.bot.get_dm_channel(player_id)

        await dm.send(embed=create_confirm_embed(game_state, self.get_game_details(game_state.game)), view=GameConfirm(self.bot, game_id), delete_after=60*15, file=file)

    # ---------------------------------------------------------------------------- #

    async def player_confirm(self, player_id: int, game_id: GameId):
        unconfirmed_list = await self.bot.game_status.player_confirm(game_id, player_id)

        if len(unconfirmed_list) == 0:
            self.bot.game_admin.game_confirmed(game_id)
    
    async def reject_game(self, game_id: GameId, rejecting_player: discord.User | discord.Member):
        game_details = await self.bot.game_status.get_game(game_id)
        
        for accepted_player_id in game_details.confirmed_players:
            try:
                await (await self.bot.get_dm_channel(accepted_player_id)).send(f'{rejecting_player.name} declined the game of {game_details.game}')
            except:
                print('User not found reject game')
        
        await self.bot.game_status.delete_game(game_id)
            
    # ---------------------------------------------------------------------------- #

    def game_confirmed(self, game_id: GameId):
        # TODO add to game status expire timer
        # TODO check if game needs to be qued
        print("hi")
        pass
    
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

# ---------------------------------------------------------------------------- #

def create_confirm_embed(game_state: GameState, game_details: GameInfo):
    message = discord.Embed(
        title=f'{game_state.player_names[game_state.starting_player]} wants to play a game!',
    )
    
    message.add_field(name='Game', value=f'{game_state.game}', inline=True)
    other_player_names = []
    for other_players_ids in game_state.player_names.keys():
        if other_players_ids != player_id and other_players_ids != game_state.starting_player:
            other_player_names.append(game_state.player_names[other_players_ids])
    print(other_player_names)
    if len(other_player_names):
        message.add_field(name='Other Players', value=', '.join(other_player_names), inline=True)
    
    file = discord.File(game_details.thumbnail_file_path, filename="abc.png")
    message.set_thumbnail(url=f'attachment://{file.filename}')
    
    if game_state.bet:
        message.add_field(name='Bet', value=game_state.bet, inline=False)
    
    return message

class GameConfirm(discord.ui.View):
    def __init__(self, bot: Bot, game_id: GameId):
        self.bot = bot
        self.game_id = game_id
        super().__init__()
    
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.bot.game_admin.player_confirm(interaction.user.id, self.game_id)
        if interaction.message:
            await interaction.message.edit(delete_after=5)
        await interaction.response.send_message('Game accepted!', delete_after=5)

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.bot.game_admin.reject_game(self.game_id, interaction.user)
        if interaction.message:
            await interaction.message.edit(delete_after=5)
        await interaction.response.send_message('Game rejected!', delete_after=5)
