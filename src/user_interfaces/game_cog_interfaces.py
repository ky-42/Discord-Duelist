from typing import Dict

import discord
from discord import ui

from data_types import GameId
from data_wrappers.game_status import GameStatus
from data_wrappers.user_status import UserStatus
from games.game_handling.game_admin import GameAdmin
from games.game_handling.game_loading import GameLoading


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


class GameReplySelect(ui.View):
    """
    Dropdown menu to select game to reply to
    """

    def __init__(
        self,
        user_notifications: Dict[GameId, GameStatus.GameState],
        interaction: discord.Interaction,
    ):
        super().__init__()

        self.game_dropdown = ui.Select(
            max_values=1, placeholder="Select a game to reply to"
        )

        self.game_dropdown.callback = GameReplySelect.game_select_callback

        for game_id, game_data in user_notifications.items():
            names = [
                game_data.player_names[str(player_id)]
                for player_id in game_data.confirmed_players
                if player_id != interaction.user.id
            ]

            game_string = f"{game_data.game} - with {', '.join(names)}"

            self.game_dropdown.add_option(label=game_string, value=game_id)

        self.add_item(self.game_dropdown)

    @staticmethod
    async def game_select_callback(interaction: discord.Interaction):
        await interaction.response.defer()

    @ui.button(label="Reply", style=discord.ButtonStyle.primary, row=1)
    async def confirm(self, interaction: discord.Interaction, _: ui.Button):
        if len(self.game_dropdown.values) > 0:
            only_game_details = await GameStatus.get(self.game_dropdown.values[0])

            await UserStatus.remove_notification(
                self.game_dropdown.values[0], interaction.user.id
            )
            await GameLoading.get_game(only_game_details.game).reply(
                self.game_dropdown.values[0], interaction
            )
        else:
            await interaction.response.defer()

    @ui.button(label="Cancel", style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()
