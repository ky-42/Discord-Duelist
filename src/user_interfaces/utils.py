"""Utility functions that are commonly used by interfaces of all types"""

from typing import Optional

import discord

from data_types import GameId, UserId
from data_wrappers.game_status import GameStatus


async def defer(interaction: discord.Interaction):
    await interaction.response.defer()


def game_description_string(
    game_status: GameStatus.Game, seeing_user: UserId, game_id: Optional[GameId] = None
) -> str:
    """Creates a string that describes a game to a specific user.

    Args:
        game_details (GameStatus.Game): Status of the game to be described.
        seeing_user (UserId): Id of user who will see this description.
        game_id (GameId, optional): Id of the game to be described.
            Defaults to None.

    Returns:
        A string that describes the a game based on the game status that
        was passed.
    """

    # Creates a list of other users in the games
    user_names = ", ".join(
        [
            name.capitalize()
            for user_id, name in game_status.usernames.items()
            if seeing_user != user_id
        ]
    )

    main_string = f"{game_status.game_module_name.capitalize()} with {user_names}"

    if game_id:
        main_string += f" ({game_id})"

    return main_string
