import importlib
import discord
import os
from data_wrappers import GameStatus
from main import Bot
from typing import List, Mapping
import redis.asyncio as redis
from games.tests import GameInfo
from types import ModuleType
from exceptions.game_exceptions import GameNotFound


class GameAdmin:
    timeout_minutes = 15

    loaded_games: dict[str, None | ModuleType] = {
        game_name: None for game_name in os.listdir("./games")
    }

    # ---------------------------------------------------------------------------- #

    def check_game_details(self, game_name: str, player_count: int) -> None:
        details = self.get_game_details(game_name)

        details.check_player_count(player_count)

    def get_game_details(self, game_name: str) -> GameInfo:
        try:
            if (game_module := self.loaded_games.get(game_name)) != None:
                return game_module.details
            return self.__load_game(game_name).details
        except:
            raise GameNotFound(game_name)

    # Not to be called externally and only if the game isnt loaded already
    def __load_game(self, game_name: str) -> ModuleType:
        game = importlib.import_module(f"games.{game_name}")
        self.loaded_games[game_name] = game
        return game

    # ---------------------------------------------------------------------------- #

    async def initialize_game(
        self,
        game_name: str,
        bet: int,
        player_one: int,
        # Does not include player one id
        secondary_player_ids: List[int],
        # Includes player one. Is in form {id: username}
        player_names: Mapping[str, str]
    ):

        game_id = GameStatus.create_game_id()

        game_details = GameStatus.GameState(
            status=0,
            game=game_name,
            bet=bet,
            starting_player=player_one,
            player_names=player_names,
            queued_players=[],
            confirmed_players=[player_one],
            unconfirmed_players=secondary_player_ids
        )

        # Adds game to game status store
        await GameStatus.add_game(
            game_id,
            game_details,
            self.timeout_minutes
        )

        # Sends out confirmations to secondary players
        await self.confirm_game(game_id, game_details)

    # ---------------------------------------------------------------------------- #

    async def confirm_game(self, game_id: GameId, game_state: GameState):
        for player_id in game_state.unconfirmed_players:
            await self.send_confirm(player_id, game_id, game_state)

    async def send_confirm(self, player_id: int, game_id: GameId, game_state: GameState):

        dm = await self.bot.get_dm_channel(player_id)

        await dm.send(
            embed=create_confirm_embed(
                game_state,
                self.get_game_details(game_state.game)
            ),
            view=GameConfirm(self.bot, game_id),
            delete_after=60*self.timeout_minutes
        )

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
            other_player_names.append(
                game_state.player_names[other_players_ids])
    print(other_player_names)
    if len(other_player_names):
        message.add_field(name='Other Players', value=', '.join(
            other_player_names), inline=True)

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
