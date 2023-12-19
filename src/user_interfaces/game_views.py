import asyncio
from typing import Awaitable, Callable, Dict

import discord
from discord import ui

from data_types import DiscordMessage, GameId, UserId
from data_wrappers.game_status import GameStatus
from user_interfaces.utils import game_description_string


class GetPlayers(ui.View):
    """
    Dropdown menu to select players for a game
    """

    def __init__(
        self,
        min: int,
        max: int,
        starting_player: UserId,
        players_selected_callback: Callable[[Dict[str, str]], Awaitable[None]],
    ):
        super().__init__()

        self.starting_player = starting_player
        self.players_selected_callback = players_selected_callback

        # Creates the dropdown menu
        self.user_select = ui.UserSelect(
            placeholder="Select a user please!",
            min_values=min - 1,
            max_values=max - 1,
            row=0,
        )
        self.add_item(self.user_select)

        # Sets a callback when a player selects a user but doesent confirm
        self.user_select.callback = self.user_select_callback

    async def user_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    @ui.button(label="Invite Players", style=discord.ButtonStyle.green, row=1)
    async def selected_players(self, interaction: discord.Interaction, _: ui.Button):
        if interaction.user.id == self.starting_player:
            # Stops user from inviting themselves
            if self.starting_player in [user.id for user in self.user_select.values]:
                return await interaction.response.send_message(
                    "Stop trying to play with yourself", ephemeral=True, delete_after=5
                )

            try:
                await self.players_selected_callback(
                    {str(player.id): player.name for player in self.user_select.values}
                )
            except Exception as e:
                await interaction.response.send_message(content=str(e), ephemeral=True)
            else:
                await interaction.response.send_message(
                    content="Game created! Please wait for other players to accept game",
                    ephemeral=True,
                    delete_after=10,
                )
            finally:
                # Deletes the message after 10 seconds
                if interaction.message:
                    await asyncio.sleep(10)
                    await interaction.followup.delete_message(interaction.message.id)

    @ui.button(label="Cancel", style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class GameConfirm(discord.ui.View):
    """
    UI for confirming a game
    """

    def __init__(
        self,
        accept_callback: Callable[[], Awaitable[None]],
        reject_callback: Callable[[], Awaitable[None]],
    ):
        super().__init__()

        self.accept_callback = accept_callback
        self.reject_callback = reject_callback

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        try:
            await self.accept_callback()
        except Exception as e:
            await interaction.response.send_message(content=str(e), ephemeral=True)
        else:
            await interaction.response.edit_message(view=None)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        try:
            await self.reject_callback()
        except Exception as e:
            await interaction.response.send_message(content=str(e), ephemeral=True)
        else:
            if interaction.message:
                await interaction.message.delete()


class GameSelect(ui.View):
    """
    Dropdown menu to select game
    """

    def __init__(
        self,
        user_id: UserId,
        game_list: Dict[GameId, GameStatus.Game],
        selected_callback: Callable[[GameId, UserId], Awaitable[DiscordMessage]],
        button_label: str,
    ):
        super().__init__()

        self.user_id = user_id
        self.reply_callback = selected_callback

        self.add_dropdown(game_list)
        self.add_select_button(button_label)
        self.add_cancel_button()

    def add_dropdown(self, game_list: Dict[GameId, GameStatus.Game]):
        self.game_dropdown = ui.Select(
            max_values=1, placeholder="Select a game to reply to"
        )

        for game_id, game_data in game_list.items():
            self.game_dropdown.add_option(
                label=game_description_string(game_data, self.user_id, game_id),
                value=game_id,
            )

        self.game_dropdown.callback = GameSelect.game_select_callback

        self.add_item(self.game_dropdown)

    @staticmethod
    async def game_select_callback(interaction: discord.Interaction):
        await interaction.response.defer()

    def add_select_button(self, button_label: str):
        self.selected_button = ui.Button(
            label=button_label, style=discord.ButtonStyle.green, row=1
        )

        self.selected_button.callback = self.select

        self.add_item(self.selected_button)

    async def select(self, interaction: discord.Interaction):
        if len(self.game_dropdown.values) > 0:
            game_reply = await self.reply_callback(
                self.game_dropdown.values[0], interaction.user.id
            )
            await interaction.response.send_message(**game_reply.for_send())
        else:
            await interaction.response.defer()

    def add_cancel_button(self):
        self.cancel_button = ui.Button(
            label="Cancel", style=discord.ButtonStyle.red, row=1
        )

        self.cancel_button.callback = self.cancel

        self.add_item(self.cancel_button)

    async def cancel(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class EmbedCycle(ui.View):
    """
    View that cycles through embeds

    Parameters
    ----------
    user_id:
        User that is supposed to interact with this view
    states:
        List of embeds with a string that will be shown on
        the button when the embed is next in cycle

        IMPORTANT: The first embed in the list must be the embed
        thats initally send with the message
    """

    def __init__(self, user_id: UserId, states: list[tuple[discord.Embed, str]]):
        super().__init__()

        self.user_id = user_id
        self.states = states

        self.state = 0

        self.switch_button = ui.Button(
            label=self.states[((self.state + 1) % len(self.states))][1],
            style=discord.ButtonStyle.green,
            row=1,
        )

        self.switch_button.callback = self.__switch_callback

        self.add_item(self.switch_button)

    async def __switch_callback(self, interaction: discord.Interaction):
        if interaction.message and interaction.user.id == self.user_id:
            self.state += 1

            self.switch_button.label = self.states[
                ((self.state + 1) % len(self.states))
            ][1]

            await interaction.response.edit_message(
                embed=self.states[((self.state) % len(self.states))][0],
                view=self,
            )

        else:
            await interaction.response.defer()
