import asyncio
from typing import Awaitable, Callable, Dict

import discord
from discord import ui

from data_types import DiscordMessage, GameId, UserId
from data_wrappers.game_status import GameStatus


class GetPlayers(ui.View):
    """
    Dropdown menu to select players for a game
    """

    def __init__(
        self,
        min: int,
        max: int,
        starting_player: UserId,
        players_selected_func: Callable[[Dict[str, str]], Awaitable[None]],
    ):
        super().__init__()

        self.starting_player = starting_player
        self.players_selected_callback = players_selected_func

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
        accept_func: Callable[[], Awaitable[None]],
        reject_func: Callable[[], Awaitable[None]],
    ):
        super().__init__()

        self.accept_func = accept_func
        self.reject_func = reject_func

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        try:
            await self.accept_func()
        except Exception as e:
            await interaction.response.send_message(content=str(e), ephemeral=True)
            # Lets user see error before deleting message
            await asyncio.sleep(10)
        finally:
            if interaction.message:
                await interaction.followup.delete_message(interaction.message.id)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        try:
            await self.reject_func()
        except Exception as e:
            await interaction.response.send_message(content=str(e), ephemeral=True)
        else:
            await interaction.response.send_message("Game rejected!", delete_after=10)

        finally:
            if interaction.message:
                await asyncio.sleep(10)
                await interaction.followup.delete_message(interaction.message.id)


class GameReplySelect(ui.View):
    """
    Dropdown menu to select game to reply to
    """

    def __init__(
        self,
        user_id: UserId,
        user_notifications: Dict[GameId, GameStatus.Game],
        reply_func: Callable[[GameId, UserId], Awaitable[DiscordMessage]],
    ):
        super().__init__()

        self.reject_func = reply_func

        self.game_dropdown = ui.Select(
            max_values=1, placeholder="Select a game to reply to"
        )

        self.game_dropdown.callback = GameReplySelect.game_select_callback

        for game_id, game_data in user_notifications.items():
            names = [
                game_data.player_names[str(player_id)]
                for player_id in game_data.all_players
                if player_id != user_id
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
            game_reply = await self.reject_func(
                self.game_dropdown.values[0], interaction.user.id
            )
            await interaction.response.send_message(**game_reply.for_send())
        else:
            await interaction.response.defer()

    @ui.button(label="Cancel", style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()
