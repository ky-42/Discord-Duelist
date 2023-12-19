import asyncio
from typing import Awaitable, Callable

import discord

from data_types import GameId

from .data import TicTacToeData


class TicTacToeButton(discord.ui.Button):
    """
    A button for the TicTacToe board

    state:
        0 = empty,
        1 = o,
        2 = x
    """

    def __init__(self, row: int, column: int, state: int):
        # Sets the button to the correct style and label
        if state == 0:
            super().__init__(
                style=discord.ButtonStyle.secondary, label="\u200B", row=row
            )
        elif state == 1:
            super().__init__(
                style=discord.ButtonStyle.success, label="o", row=row, disabled=True
            )
        elif state == 2:
            super().__init__(
                style=discord.ButtonStyle.danger, label="x", row=row, disabled=True
            )

        self.row = row
        self.column = column

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None

        await self.view.pressed(self.row, self.column, interaction, self)


class TicTacToeView(discord.ui.View):

    """
    The view for the TicTacToe game which mainly
    consists of the board of buttons
    """

    def __init__(
        self,
        game_id: GameId,
        game_data: TicTacToeData,
        # The callback to call when a button is pressed
        pressed_callback: Callable[
            [GameId, int, int, discord.Interaction], Awaitable[None]
        ],
    ):
        super().__init__()
        self.game_id = game_id
        self.game_data = game_data
        self.pressed_callback = pressed_callback

        # Creates the board of buttons
        for row in range(3):
            for column in range(3):
                self.add_item(
                    TicTacToeButton(
                        row, column, self.game_data.active_board[row][column]
                    )
                )

        self.active_user = game_data.active_user
        self.update_state = game_data.user_square_type[str(self.active_user)]

    async def pressed(
        self,
        row: int,
        column: int,
        interaction: discord.Interaction,
        button: TicTacToeButton,
    ):
        if self.active_user == interaction.user.id:
            # Updates the button to the correct
            # style and label on the active view
            if self.update_state == 1:
                button.style = discord.ButtonStyle.success
                button.label = "o"
            elif self.update_state == 2:
                button.style = discord.ButtonStyle.danger
                button.label = "x"

            # Disables buttons and stops the view
            for item in self.children:
                if item is discord.Button:
                    item.disabled = True
            self.stop()

            await interaction.response.edit_message(view=self)

            await self.pressed_callback(self.game_id, row, column, interaction)

            # Deletes ui 5 seconds after playing move
            if interaction.message:
                await asyncio.sleep(5)
                await interaction.followup.delete_message(interaction.message.id)
        else:
            # Ignore the button press not by the active user
            await interaction.response.defer()
