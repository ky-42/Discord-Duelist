import importlib
import discord
import os
from data_wrappers import GameId, GameStatus
from bot import bot
from typing import List, Mapping
import redis.asyncio as redis
from games.tests import GameInfo
from types import ModuleType
from exceptions.game_exceptions import GameNotFound

class GameAdmin:
    timeout_minutes = 15

    # Stores the loaded game moduels
    loaded_games: dict[str, None | ModuleType] = {
        game_name: None for game_name in os.listdir("./games")
    }

    # ---------------------------------------------------------------------------- #

    @staticmethod
    def check_game_details(game_name: str, player_count: int) -> None:
        details = GameAdmin.get_game_details(game_name)

        details.check_player_count(player_count)

    @staticmethod
    def get_game_details(game_name: str) -> GameInfo:
        """
        Loads the game module if it isnt loaded already and returns the details
        Each moduel should have a details attribute which is a GameInfo object at the top level
        """

        try:
            if (game_module := GameAdmin.loaded_games.get(game_name)) != None:
                return game_module.details
            return GameAdmin.__load_game(game_name).details
        except:
            raise GameNotFound(game_name)

    # Not to be called externally and only if the game isnt loaded already
    @staticmethod
    def __load_game(game_name: str) -> ModuleType:
        game = importlib.import_module(f"games.{game_name}")
        GameAdmin.loaded_games[game_name] = game
        return game

    # ---------------------------------------------------------------------------- #

    @staticmethod
    async def initialize_game(
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
            confirmed_players=[player_one],
            unconfirmed_players=secondary_player_ids
        )

        # Adds game to game status store
        await GameStatus.add_game(
            game_id,
            game_details,
            GameAdmin.timeout_minutes
        )

        # Sends out confirmations to secondary players
        await GameAdmin.confirm_game(game_id, game_details)

    # ---------------------------------------------------------------------------- #

    @staticmethod
    async def confirm_game(game_id: GameId, game_state: GameStatus.GameState):
        for player_id in game_state.unconfirmed_players:
            await GameAdmin.send_confirm(player_id, game_id, game_state)

    @staticmethod
    async def send_confirm(player_id: int, game_id: GameId, game_state: GameStatus.GameState):

        # Gets the dm channel of the player to send the confirmation over
        dm = await bot.get_dm_channel(player_id)

        await dm.send(
            embed=create_confirm_embed(
                player_id,
                game_state,
                GameAdmin.get_game_details(game_state.game)
            ),
            view=GameConfirm(game_id),
            delete_after=60*GameAdmin.timeout_minutes
        )

    # ---------------------------------------------------------------------------- #

    @staticmethod
    async def player_confirm(player_id: int, game_id: GameId):
        unconfirmed_list = await GameStatus.player_confirm(game_id, player_id)

        if len(unconfirmed_list) == 0:
            GameAdmin.game_confirmed(game_id)

    @staticmethod
    async def reject_game(game_id: GameId, rejecting_player: discord.User | discord.Member):
        game_details = await GameStatus.get_game(game_id)

        # Notifies players that have accepted the game that it has been cancelled
        for accepted_player_id in game_details.confirmed_players:
            try:
                await (await bot.get_dm_channel(accepted_player_id)).send(f'{rejecting_player.name} declined the game of {game_details.game}')
            except:
                print('User not found reject game')

        await GameStatus.delete_game(game_id)

    # ---------------------------------------------------------------------------- #

    @staticmethod
    def game_confirmed(game_id: GameId):
        # TODO add to game status expire timer
        # TODO check if game needs to be qued
        print("hi")
        pass

    @staticmethod
    def start_game(game_id: GameId):
        pass

    @staticmethod
    def game_end():
        pass

    @staticmethod
    def cancel_game(game_id: GameId):
        pass

    # Run this when there is an error and a game need to be cleaned up when not initilized
    # or half way through function
    @staticmethod
    def clear_game(game_id: GameId):
        pass

# ---------------------------------------------------------------------------- #

def create_confirm_embed(player_id: int, game_state: GameStatus.GameState, game_details: GameInfo) -> discord.Embed:
    message_embed = discord.Embed(
        title=f'{game_state.player_names[str(game_state.starting_player)]} wants to play a game!',
    )

    message_embed.add_field(name='Game', value=f'{game_state.game}', inline=True)

    # Gets list of other request users names
    other_player_names = [
        game_state.player_names[other_players_ids]
        for other_players_ids in game_state.player_names.keys()
        if other_players_ids != player_id
            and other_players_ids != game_state.starting_player
    ]

    # Adds other players names to embed
    if len(other_player_names):
        message_embed.add_field(name='Other Players', value=', '.join(
            other_player_names), inline=True)

    # Adds game thumbnail to embed
    file = discord.File(game_details.thumbnail_file_path, filename="abc.png")
    message_embed.set_thumbnail(url=f'attachment://{file.filename}')

    # Adds bet to embed
    if game_state.bet:
        message_embed.add_field(name='Bet', value=game_state.bet, inline=False)

    return message_embed


class GameConfirm(discord.ui.View):
    """
    UI for confirming a game
    """

    def __init__(self, game_id: GameId):
        self.game_id = game_id
        super().__init__()

    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        await GameAdmin.player_confirm(interaction.user.id, self.game_id)

        # Will delete interaction after 5 seconds
        if interaction.message:
            await interaction.message.edit(delete_after=5)

        await interaction.response.send_message('Game accepted!', delete_after=5)

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        await GameAdmin.reject_game(self.game_id, interaction.user)

        # Will delete interaction after 5 seconds
        if interaction.message:
            await interaction.message.edit(delete_after=5)

        await interaction.response.send_message('Game rejected!', delete_after=5)
