"""Interfaces that are sent as a discord.py view.

All classes in this module should be instanced then sent as
part of a message.

Typical usage example:

    await user.send_message(
        ...,
        view=GetUsers(
            min,
            max,
            starting_user,
            users_selected_callback,
        ),
        ...
    )
"""

import asyncio
import traceback
from typing import Awaitable, Callable, Dict

import discord
from discord import ui

from data_types import DiscordMessage, GameId, UserId
from data_wrappers.game_status import GameStatus
from user_interfaces.utils import defer, game_description_string


class GetUsers(ui.View):
    """Dropdown menu to select a list of users.

    Lets user select other users from dropdown menu limiting the
    number of users that can be selected. Also will not let the user
    who recicives this interface select themselves. When user is finished
    they press confirm button.
    """

    def __init__(
        self,
        user_id: UserId,
        min_users: int,
        max_users: int,
        users_selected_callback: Callable[[Dict[str, str]], Awaitable[DiscordMessage]],
    ):
        """
        Args:
            min_users (int): Minimum number of users that must be selected.
            max_users (int): Maximum number of users that can be selected.
            user_id (UserId): Id of user the view will be sent to.
            users_selected_callback (Callable[[Dict[str, str]], Awaitable[DiscordMessage]]):
                Function that is called when user if finished selecting other
                users and presses confirm button. Function will be passed dict of format
                {user_id: username} where each entry is a based on selected user. Should
                also return a DiscordMessage object that will be sent to user after callback
                runs successfully.
        """

        super().__init__()

        self.__starting_user = user_id
        self.__users_selected_callback = users_selected_callback

        # Creates the dropdown menu
        self.__user_select = ui.UserSelect(
            placeholder="Select a user please!",
            min_values=min_users,
            max_values=max_users,
            row=0,
        )
        self.add_item(self.__user_select)

        self.min_users = min_users
        self.max_users = max_users

        # Sets a callback when a user selects a user but doesent confirm
        self.__user_select.callback = defer

    @ui.button(label="Confirm", style=discord.ButtonStyle.green, row=1)
    async def __users_selected(
        self, interaction: discord.Interaction, _: ui.Button
    ) -> None:
        selected_users = {str(user.id): user.name for user in self.__user_select.values}

        # Checks if user selected themself
        if str(self.__starting_user) in selected_users.keys():
            return await interaction.response.send_message(
                "Stop trying to play with yourself", ephemeral=True, delete_after=5
            )

        if (
            not len(selected_users)
            or self.min_users > len(selected_users)
            or self.max_users < len(selected_users)
        ):
            return await interaction.response.send_message(
                "Invalid number of users!", ephemeral=True, delete_after=5
            )

        try:
            callback_message = await self.__users_selected_callback(selected_users)

        except:
            print(traceback.format_exc())
            await interaction.response.send_message(
                content="Something went wrong", ephemeral=True
            )

        else:
            await interaction.response.send_message(**callback_message.for_send())

        finally:
            # Deletes the message after 10 seconds
            if interaction.message:
                await asyncio.sleep(10)
                await interaction.followup.delete_message(interaction.message.id)

    @ui.button(label="Cancel", style=discord.ButtonStyle.red, row=1)
    async def __cancel(self, interaction: discord.Interaction, _: ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class InviteOptions(discord.ui.View):
    """Buttons for accepting or rejecting.

    Renders a greeen buttton that says "Accept" and a red button
    that says "Reject". When pressed they will call their respective
    callback. When "Accept" is pressed the buttons will be removed but
    the message will stay. When "Reject" is pressed bot the buttons
    and the message will be deleted.
    """

    def __init__(
        self,
        accept_callback: Callable[[], Awaitable[None]],
        reject_callback: Callable[[], Awaitable[None]],
    ):
        """
        Args:
            accept_callback (Callable[[], Awaitable[None]]):
                Function called when "Accept" button is pressed.
            reject_callback (Callable[[], Awaitable[None]]):
                Function called when "Reject" button is pressed.
        """

        super().__init__()

        self.__accept_callback = accept_callback
        self.__reject_callback = reject_callback

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def __accept(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        try:
            await self.__accept_callback()

        except:
            print(traceback.format_exc())
            await interaction.response.send_message(
                content="Something went wrong", ephemeral=True
            )

        else:
            await interaction.response.edit_message(view=None)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def __reject(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        try:
            await self.__reject_callback()

        except:
            print(traceback.format_exc())
            await interaction.response.send_message(
                content="Something went wrong", ephemeral=True
            )

        else:
            if interaction.message:
                await interaction.message.delete()


class GameSelect(ui.View):
    """Dropdown of games to select and buttons to select and cancel.

    Lists games in a dropdown menu where user can select one. There are
    two buttons "Select" which will call the selected_callback and
    "Cancel" which will just delete the interface.
    """

    def __init__(
        self,
        user_id: UserId,
        game_list: Dict[GameId, GameStatus.Game],
        selected_callback: Callable[[GameId, UserId], Awaitable[DiscordMessage]],
        button_label: str,
    ):
        """
        Args:
            user_id (UserId): Id of user the interface will be sent to.
            game_list (Dict[GameId, GameStatus.Game]): Dict that has game
                id's as keys and game status as value. These are what will
                be listed in the dropdown.
            selected_callback (Callable[[GameId, UserId], Awaitable[DiscordMessage]]):
                Function that is called when the "Select" button is pressed. Will be
                called with the selected games id and the id of the user who was sent
                the interface. Should return a DiscordMessage that will be sent to the
                user.
            button_label (str): Label for the select button
        """

        super().__init__()

        self.__user_id = user_id
        self.__reply_callback = selected_callback

        # Adds interface elements
        self.__add_dropdown(game_list)
        self.__add_select_button(button_label)
        self.__add_cancel_button()

    def __add_dropdown(self, game_list: Dict[GameId, GameStatus.Game]) -> None:
        self.game_dropdown = ui.Select(
            max_values=1, placeholder="Select a game to reply to"
        )

        for game_id, game_data in game_list.items():
            self.game_dropdown.add_option(
                label=game_description_string(game_data, self.__user_id, game_id),
                value=game_id,
            )

        self.game_dropdown.callback = defer

        self.add_item(self.game_dropdown)

    def __add_select_button(self, button_label: str) -> None:
        self.selected_button = ui.Button(
            label=button_label, style=discord.ButtonStyle.green, row=1
        )

        self.selected_button.callback = self.__select

        self.add_item(self.selected_button)

    async def __select(self, interaction: discord.Interaction) -> None:
        if len(self.game_dropdown.values) > 0:
            game_reply = await self.__reply_callback(
                self.game_dropdown.values[0], interaction.user.id
            )
            await interaction.response.send_message(**game_reply.for_send())
        else:
            await interaction.response.defer()

    def __add_cancel_button(self) -> None:
        self.cancel_button = ui.Button(
            label="Cancel", style=discord.ButtonStyle.red, row=1
        )

        self.cancel_button.callback = self.__cancel

        self.add_item(self.cancel_button)

    async def __cancel(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class EmbedCycle(ui.View):
    """Cycles through list of embeds based on button presses.

    Creates a button that when pressed will change the embed in
    the connected message to the next in a list of passed embeds.
    The first embed in the list must be sent with the connected
    message.
    """

    def __init__(self, states: list[tuple[discord.Embed, str]]):
        """
        Args:
            states (list[tuple[discord.Embed, str]]):
                List of embeds and the text that should be on
                the button when it is next to be shown.
        """

        super().__init__()

        self.states = states

        self.state = 0

        self.switch_button = ui.Button(
            label=self.states[((self.state + 1) % len(self.states))][1],
            style=discord.ButtonStyle.green,
            row=1,
        )

        self.switch_button.callback = self.__switch_callback

        self.add_item(self.switch_button)

    async def __switch_callback(self, interaction: discord.Interaction) -> None:
        if interaction.message:
            self.state += 1

            # Sets button label next state
            self.switch_button.label = self.states[
                ((self.state + 1) % len(self.states))
            ][1]

            await interaction.response.edit_message(
                embed=self.states[((self.state) % len(self.states))][0],
                view=self,
            )

        else:
            await interaction.response.defer()
