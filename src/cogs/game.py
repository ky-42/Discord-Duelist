from datetime import timedelta
from typing import List

import discord
from discord import app_commands, ui
from discord.ext import commands

from bot import Bot
from data_wrappers import GameStatus, UserStatus
from games.game_handling.game_admin import GameAdmin
from games.game_handling.game_loading import GameLoading


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
        When ran this will check if the user is in a game and if they are check if it is their turn
        and if it is send them the game UI
        """
        if game_id := await UserStatus.check_in_game(interaction.user.id):
            game_details = await GameStatus.get_game(game_id)
            await GameLoading.get_game(game_details.game).reply(game_id, interaction)

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


class GetPlayersClassInner(ui.View):
    """
    Dropdown menu to select players for a game
    """

    def __init__(self, game_name: str, min: int, max: int):
        super().__init__()
        self.game_name = game_name

        # Creates the dropdown menu
        self.user_select = ui.UserSelect(
            placeholder="Select a user please!",
            min_values=min - 1,
            max_values=max - 1,
            row=0,
            custom_id="user-select",
        )
        self.add_item(self.user_select)

        # Sets a callback when a player selects a user but doesent confirm
        self.user_select.callback = self.user_select_callback

    async def user_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    @ui.button(label="Confirm Players", style=discord.ButtonStyle.green, row=1)
    async def confirm(self, interaction: discord.Interaction, _: ui.Button):
        player_one = interaction.user
        secondary_players = self.user_select.values

        # Double checks that the number of players is allowed. Just in case
        if GameLoading.check_game_details(self.game_name, len(secondary_players) + 1):
            await GameAdmin.initialize_game(
                game_name=self.game_name,
                bet=0,
                player_one=player_one.id,
                secondary_player_ids=[player.id for player in self.user_select.values],
                player_names={
                    str(player.id): player.name
                    for player in (secondary_players + [player_one])
                },
            )
            return await interaction.response.defer()

        else:
            return await interaction.response.send_message(
                content="Problem with request", ephemeral=True
            )

    @ui.button(label="Cancel Game", style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


async def setup(bot: Bot) -> None:
    await bot.add_cog(Game())
