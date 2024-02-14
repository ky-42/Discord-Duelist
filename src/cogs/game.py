"""Contains game cog, which is used to interact with and play games"""

import functools
from datetime import timedelta
from typing import Dict, List

import discord
from discord import app_commands
from discord.ext import commands

from bot import Bot
from data_types import GameId
from data_wrappers import GameStatus, UserStatus
from exceptions import GameNotFound
from game_handling import GameAdmin
from game_modules import GameModuleLoading
from user_interfaces.game_embeds import game_list_embed
from user_interfaces.game_views import EmbedCycle, GameSelect, GetUsers


class Game(commands.Cog):
    """Commands used to interact with games"""

    def __init__(self) -> None:
        super().__init__()

    @app_commands.command(name="play", description="Play a game!")
    async def play(self, interaction: discord.Interaction, game_name: str) -> None:
        """Starts the process of creating a game"""

        game_object = GameStatus.Game(
            state=0,
            game_module_name=game_name,
            starting_user=interaction.user.id,
            usernames={str(interaction.user.id): interaction.user.name},
            all_users=[interaction.user.id],
            pending_users=[],
        )

        game_module_details = GameModuleLoading.get_game_module(game_name).get_details()

        # Sends user UI to select users they would like to play with
        return await interaction.response.send_message(
            content="Please select the users you want to play with",
            view=GetUsers(
                interaction.user.id,
                game_module_details.min_users,
                game_module_details.max_users,
                # Partial is used to pass the game object to the callback letting
                # the ui be decoupled from the game object
                functools.partial(GameAdmin.users_selected, game_object),
            ),
            delete_after=timedelta(minutes=5).total_seconds(),
            ephemeral=True,
        )

    @play.autocomplete("game_name")
    async def play_autocomplete(
        self, _interaction: discord.Interaction, current_input: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for game options in the play command.

        Will return the first 25 matches.
        """

        games_list = GameModuleLoading.list_all_game_modules()

        partial_matches = list(
            filter(lambda x: current_input.lower() in x.lower(), games_list)
        )

        # Returns the first 25 matches
        return [
            app_commands.Choice(name=game_name, value=game_name)
            for game_name in partial_matches[: max(len(partial_matches), 25)]
        ]

    @app_commands.command(name="reply", description="Reply to a game")
    async def reply(self, interaction: discord.Interaction) -> None:
        """Lets user reply/interact with a game they are in.

        When ran this will check if the user is in a game and if they are
        it will either ask them to select the game they want to play and
        just send the interaction to the game class (or skip the select part if they
        are only in one game).
        """

        if user_status := await UserStatus.get(interaction.user.id):
            user_notifications = user_status.notifications

            # If there is only only one game then just send the game the interaction
            if len(user_notifications) == 1:
                game_reply = await GameAdmin.reply(
                    user_notifications[0], interaction.user.id
                )
                return await interaction.response.send_message(**game_reply.for_send())

            game_details: Dict[GameId, GameStatus.Game] = {}
            for game_id in user_notifications:
                try:
                    active_game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.remove_notification(interaction.user.id, game_id)
                else:
                    if active_game_details.state == 2:
                        game_details[game_id] = active_game_details

            # Send a dropdown to select a game if there are multiple games
            if len(game_details) > 0:
                return await interaction.response.send_message(
                    content="Please select the game you want to play",
                    ephemeral=True,
                    view=GameSelect(
                        interaction.user.id, game_details, GameAdmin.reply, "Reply"
                    ),
                )

        return await interaction.response.send_message(
            content="You have no games to reply to", ephemeral=True
        )

    @app_commands.command(name="status", description="List the games you are in")
    async def status(self, interaction: discord.Interaction) -> None:
        """Used to see all the games a user is in"""

        if user_status := await UserStatus.get(interaction.user.id):
            user_id = interaction.user.id

            queued_game_details: Dict[GameId, GameStatus.Game] = {}
            for game_id in user_status.queued_games:
                try:
                    game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.clear_game([user_id], game_id)
                else:
                    if game_details.state == 1:
                        queued_game_details[game_id] = game_details
                    else:
                        print("Game should be queued")

            active_game_details: Dict[GameId, GameStatus.Game] = {}
            for game_id in user_status.active_games:
                try:
                    game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.clear_game([user_id], game_id)
                else:
                    if game_details.state == 2:
                        active_game_details[game_id] = game_details
                    else:
                        print("Game should be active")

            return await interaction.response.send_message(
                embed=(
                    active_embed := game_list_embed(user_id, True, active_game_details)
                ),
                view=EmbedCycle(
                    [
                        (
                            active_embed,
                            "View Active Games",
                        ),
                        (
                            game_list_embed(user_id, False, queued_game_details),
                            "View Queued Games",
                        ),
                    ],
                ),
                ephemeral=True,
            )

        return await interaction.response.send_message(
            content="You are not in any games", ephemeral=True
        )

    @app_commands.command(name="quit", description="Leave a game")
    async def quit(self, interaction: discord.Interaction) -> None:
        """Sends user list of games they can leave with ability to select one"""

        if user_status := await UserStatus.get(interaction.user.id):
            all_games = user_status.active_games + user_status.queued_games

            game_details: Dict[GameId, GameStatus.Game] = {}
            for game_id in all_games:
                try:
                    current_game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.clear_game([interaction.user.id], game_id)
                else:
                    if current_game_details.state in [1, 2]:
                        game_details[game_id] = current_game_details

            # Send a dropdown to select a game to quit
            if len(game_details) > 0:
                return await interaction.response.send_message(
                    content="Please select the game you want to quit",
                    ephemeral=True,
                    view=GameSelect(
                        interaction.user.id, game_details, GameAdmin.quit_game, "Quit"
                    ),
                )

        return await interaction.response.send_message(
            content="You are not in any games", ephemeral=True
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Game())
