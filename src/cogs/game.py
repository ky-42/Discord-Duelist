from datetime import timedelta
from typing import Dict, List

import discord
from discord import app_commands, ui
from discord.ext import commands

from bot import Bot
from data_types import GameId
from data_wrappers import GameStatus, UserStatus
from exceptions.game_exceptions import GameNotFound
from games.game_handling.game_loading import GameLoading
from user_interfaces.game_cog_interfaces import GameReplySelect, GetPlayersClassInner


class Game(commands.GroupCog, name="game"):
    """
    Commands used to interact with games
    """

    def __init__(self) -> None:
        super().__init__()

    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction, game_name: str) -> None:
        """
        Starts the process of creating a game
        """
        try:
            game_details = GameLoading.get_game(game_name).get_details()

            # Sends out UI to select players this is done to avoid the users
            # having to type out the names in inital interaction
            # instead they can just select the users from a dropdown menu
            return await interaction.response.send_message(
                content="Please select the players you want to play with",
                ephemeral=True,
                view=GetPlayersClassInner(
                    game_name=game_name,
                    max=game_details.max_players,
                    min=game_details.min_players,
                ),
                delete_after=timedelta(minutes=5).total_seconds(),
            )

        except Exception as e:
            return await interaction.response.send_message(e)

    @play.autocomplete("game_name")
    async def play_autocomplete(
        self, _interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for game options in the play command
        """
        games_list = GameLoading.list_all_games()

        # Gets list of game names that contain the current string
        partial_matches = list(
            filter(lambda x: current.lower() in x.lower(), games_list)
        )

        # Returns the first 25 matches
        return [
            app_commands.Choice(name=game_name, value=game_name)
            for game_name in partial_matches[: max(len(partial_matches), 25)]
        ]

    @app_commands.command(name="reply")
    async def reply(self, interaction: discord.Interaction):
        """
        When ran this will check if the user is in a game and if they are
        it will either ask them to select the game they want to play and
        just send the interaction to the game class (or skip the select part if they
        are only in one game).
        """
        if user_status := await UserStatus.get_status(interaction.user.id):
            user_notifications = user_status.notifications

            # If there is only only one game then just send the game the interaction
            if len(user_notifications) == 1:
                only_game_details = await GameStatus.get(user_notifications[0])
                await UserStatus.remove_notification(
                    user_notifications[0], interaction.user.id
                )
                await GameLoading.get_game(only_game_details.game).reply(
                    user_notifications[0], interaction
                )
                return

            # For all notifications get the game data associated with it
            game_details: Dict[GameId, GameStatus.GameState] = {}

            for game_id in user_notifications:
                try:
                    current_game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.remove_notification(game_id, interaction.user.id)
                else:
                    if current_game_details.status == 2:
                        game_details[game_id] = current_game_details

            # Send a dropdown to select a game if there are multiple games
            if len(game_details) > 0:
                return await interaction.response.send_message(
                    content="Please select the game you want to play",
                    ephemeral=True,
                    view=GameReplySelect(game_details, interaction),
                )

    # @app_commands.command(name="queue")
    # async def queue(self, interaction: discord.Interaction) -> None:
    #     await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

    # @app_commands.command(name="status")
    # async def status(self, interaction: discord.Interaction) -> None:
    #     await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

    @app_commands.command(name="quit")
    async def quit(self, interaction: discord.Interaction) -> None:
        interaction.user.id
        # await GameAdmin.cancel_game()
        await interaction.response.send_message(
            "Hello from sub command 1", ephemeral=True
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Game())
