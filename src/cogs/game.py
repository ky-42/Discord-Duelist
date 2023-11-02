import functools
from datetime import timedelta
from typing import Dict, List

import discord
from discord import User, app_commands
from discord.ext import commands

from bot import Bot
from data_types import GameId
from data_wrappers import GameStatus, UserStatus
from exceptions import GameNotFound
from games.game_handling.game_actions import GameActions
from games.game_handling.game_admin import GameAdmin
from games.game_handling.game_loading import GameLoading
from user_interfaces.game_embeds import game_info_embed
from user_interfaces.game_views import EmbedCycle, GameSelect, GetPlayers


class Game(commands.GroupCog, name="game"):
    """
    Commands used to interact with games
    """

    def __init__(self) -> None:
        super().__init__()

    @app_commands.command(name="play", description="Play a game!")
    async def play(self, interaction: discord.Interaction, game_name: str) -> None:
        """
        Starts the process of creating a game
        """

        game_object = GameStatus.Game(
            status=0,
            game=game_name,
            starting_player=interaction.user.id,
            player_names={str(interaction.user.id): interaction.user.name},
            all_players=[interaction.user.id],
            unconfirmed_players=[],
        )

        game_details = GameLoading.get_game(game_name).get_details()

        # Sends out UI to select players this is done to avoid the users
        # having to type out the names in inital interaction
        # instead they can just select the users from a dropdown menu
        return await interaction.response.send_message(
            content="Please select the players you want to play with",
            view=GetPlayers(
                game_details.min_players,
                game_details.max_players,
                interaction.user.id,
                # Partial is used to pass the game object to the callback letting
                # the ui be decoupled from the game object
                functools.partial(GameAdmin.players_selected, game_object),
            ),
            delete_after=timedelta(minutes=5).total_seconds(),
            ephemeral=True,
        )

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

    @app_commands.command(name="reply", description="Reply to a game")
    async def reply(self, interaction: discord.Interaction):
        """
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

            # Gets the game details associated with the notifications
            game_details: Dict[GameId, GameStatus.Game] = {}
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
                    view=GameSelect(
                        interaction.user.id, game_details, GameAdmin.reply, "Reply"
                    ),
                )

        return await interaction.response.send_message(
            content="You have no games to reply to", ephemeral=True
        )

    @app_commands.command(name="status", description="List your games")
    async def status(self, interaction: discord.Interaction) -> None:
        """
        Used to see all the games a user is in
        """

        if user_status := await UserStatus.get(interaction.user.id):
            user_id = interaction.user.id

            queued_game_details: Dict[GameId, GameStatus.Game] = {}
            for game_id in user_status.queued_games:
                try:
                    game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.clear_game(game_id, [user_id])
                else:
                    if game_details.status == 1:
                        queued_game_details[game_id] = game_details
                    else:
                        print("Game should be queued")

            current_game_details: Dict[GameId, GameStatus.Game] = {}
            for game_id in user_status.current_games:
                try:
                    game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.clear_game(game_id, [user_id])
                else:
                    if game_details.status == 2:
                        current_game_details[game_id] = game_details
                    else:
                        print("Game should be active")

            return await interaction.response.send_message(
                embed=(
                    active_embed := game_info_embed(current_game_details, user_id, True)
                ),
                view=EmbedCycle(
                    user_id,
                    [
                        (
                            active_embed,
                            "View Active Games",
                        ),
                        (
                            game_info_embed(queued_game_details, user_id, False),
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
        """
        Sends user list of games they can leave with ability to select one
        """

        # Gets all of the users games and creates a dict with
        # game_id: Description of game
        if user_status := await UserStatus.get(interaction.user.id):
            all_games = user_status.current_games + user_status.queued_games

            # Gets the game details
            game_details: Dict[GameId, GameStatus.Game] = {}
            for game_id in all_games:
                try:
                    current_game_details = await GameStatus.get(game_id)
                except GameNotFound:
                    await UserStatus.clear_game(game_id, [interaction.user.id])
                else:
                    if current_game_details.status == 2:
                        game_details[game_id] = current_game_details

            # Send a dropdown to select a game if there are multiple games
            if len(game_details) > 0:
                return await interaction.response.send_message(
                    content="Please select the game you want to quit",
                    ephemeral=True,
                    view=GameSelect(
                        interaction.user.id, game_details, GameActions.quit_game, "Quit"
                    ),
                )

        return await interaction.response.send_message(
            content="You are not in any games", ephemeral=True
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Game())
