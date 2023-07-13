import importlib
import discord
import os
from data_wrappers import GameStatus, UserStatus, GameData
from data_types import GameId
from bot import bot
from typing import List, Mapping
import redis.asyncio as redis
from games.utils import GameInfo
from types import ModuleType
from exceptions.game_exceptions import GameNotFound

class GameAdmin:
    # Stores the loaded game moduels
    loaded_games: dict[str, None | ModuleType] = {
        game_name: None for game_name in os.listdir("./games/game_modules")
    }

    # ---------------------------------------------------------------------------- #

    @staticmethod
    def check_game_details(game_name: str, player_count: int) -> None:
        details = GameAdmin.get_game(game_name).details

        details.check_player_count(player_count)

    @staticmethod
    def get_game(game_name: str) -> ModuleType:
        """
        Loads the game module if it isnt loaded already and returns the details
        Each moduel should have a details attribute which is a GameInfo object at the top level
        """

        try:
            if (game_module := GameAdmin.loaded_games.get(game_name)) != None:
                return game_module
            return GameAdmin.__load_game(game_name)
        except:
            raise GameNotFound(game_name)

    # Not to be called externally and only if the game isnt loaded already
    @staticmethod
    def __load_game(game_name: str) -> ModuleType:
        # Watch out any errors initalizing this are caught by the caller
        # so you won't see module errors
        game = importlib.import_module(f"games.game_modules.{game_name}")
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
            bot.game_requested_expiery
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
                GameAdmin.get_game(game_state.game).details
            ),
            view=GameConfirm(game_id),
            delete_after=bot.game_requested_expiery
        )

    # ---------------------------------------------------------------------------- #

    @staticmethod
    async def player_confirm(player_id: int, game_id: GameId):
        #TODO maybe redo this part
        print('player confirm')
        unconfirmed_list = await GameStatus.player_confirm(game_id, player_id)

        if len(unconfirmed_list) == 0:
            print('player confirm')
            await GameAdmin.game_confirmed(game_id)

    @staticmethod
    async def reject_game(game_id: GameId, rejecting_player: discord.User | discord.Member):
        game_details = await GameStatus.get_game(game_id)

        for player_id in game_details.confirmed_players:
            await bot.get_user(int(player_id)).send(
                f'{rejecting_player.name} has rejected the game of {game_details.game} the you accepted'
            )
        
        await GameAdmin.cancel_game(game_id)

    # ---------------------------------------------------------------------------- #

    @staticmethod
    async def game_confirmed(game_id: GameId):
        # TODO add to game status expire timer
        # TODO check if game needs to be qued

        print(1)
        
        game_details = await GameStatus.get_game(game_id)


        for player_id in game_details.confirmed_players:
            await UserStatus.join_game(player_id, game_id)

        print(2)

        await GameAdmin.start_game(game_id)
            

    @staticmethod
    async def start_game(game_id: GameId):
        game_details = await GameStatus.get_game(game_id)

        if await UserStatus.check_users_are_ready(game_id, game_details.confirmed_players):

            for player_id in game_details.confirmed_players:
                # a = list(game_details.player_names.values())

                # if player_id != game_details.starting_player:
                #     a.remove(game_details.player_names[str(game_details.starting_player)])
                # a.remove(game_details.player_names[str(player_id)])

                # b = ', '.join(a[:-1]) + ' and ' + a[-1]

                c = f'Game of {game_details.game} is starting!'

                await (await bot.get_user(int(player_id))).send(
                    c
                )

            game_module = GameAdmin.get_game(game_details.game)
            
            print(3)
            await GameStatus.set_game_in_progress(game_id)
            await game_module.start_game(game_id)

        else:
            print(4)
            await GameStatus.set_game_queued(game_id)


    @staticmethod
    async def game_end(game_id: GameId, winner: int):
        # TODO update player status and call check game status to see if game needs to
        # next queued game to see if all players are ready now

        # This needs to be done first before the game is deleted
        game_details = await GameStatus.get_game(game_id)
        
        # Checks if after players were removed from the game if they are in another game that can start
        await UserStatus.clear_game(game_id, game_details.confirmed_players)
        for player_id in game_details.confirmed_players:
            if (user_new_game_id := await UserStatus.check_in_game(player_id)) != None:
                await GameAdmin.start_game(user_new_game_id)

                
        await GameStatus.delete_game(game_id)
        await GameData.delete_data(game_id)

    @staticmethod
    async def cancel_game(game_id: GameId):
        # Clear all game data from redis
        # so update user status, remove game status, and game data

        game_details = await GameStatus.get_game(game_id)

        if game_details.status == 0:
            # unconfirmed so just remove 
            # Notifies players that have accepted the game that it has been cancelled
            for accepted_player_id in game_details.confirmed_players:
                try:
                    await (await bot.get_dm_channel(accepted_player_id)).send(f'A player declined the game of {game_details.game}')
                except:
                    print('User not found reject game')

            await GameStatus.delete_game(game_id)
        
        elif game_details.status == 1:
            # confirmed but queued so remove from queue and and clear game status
            for accepted_player_id in game_details.confirmed_players:
                try:
                    await (await bot.get_dm_channel(accepted_player_id)).send(f'Game of {game_details.game} has been cancelled')
                except:
                    print('User not found cancel qued')

            await GameStatus.delete_game(game_id)
            await UserStatus.clear_game(game_id, game_details.confirmed_players + game_details.unconfirmed_players)
        
        
        elif game_details.status == 2:
            # game has started so remove from player status, clear game data and clear game status
            for accepted_player_id in game_details.confirmed_players:
                try:
                    await (await bot.get_dm_channel(accepted_player_id)).send(f'Game of {game_details.game} has been cancelled')
                except:
                    print('User not found cancel qued')
            
            await GameStatus.delete_game(game_id)
            await UserStatus.clear_game(game_id, game_details.confirmed_players + game_details.unconfirmed_players)
            await GameData.delete_data(game_id)
    
    
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
        # Will delete interaction after 5 seconds
        # if interaction.message:
        #     await interaction.message.edit(delete_after=5)

        await interaction.response.send_message('Game accepted!')

        await GameAdmin.player_confirm(interaction.user.id, self.game_id)


    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        await GameAdmin.cancel_game(self.game_id)

        # Will delete interaction after 5 seconds
        if interaction.message:
            await interaction.message.edit(delete_after=5)

        await interaction.response.send_message('Game rejected!', delete_after=5)
