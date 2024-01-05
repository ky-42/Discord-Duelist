"""Interfaces that are sent as an embed message.

All classes in this module should be instanced then sent as
part of a message.

Typical usage example:
    await user.send(
        ...,
        embed=game_info_embed(
            user_id,
            title,
            game_status,
            game_details,
        ),
        ...
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

import discord

from data_types import GameId, UserId
from user_interfaces.utils import game_description_string

# Stops circular import
if TYPE_CHECKING:
    from data_wrappers.game_status import GameStatus
    from game_modules.game_classes import GameModuleDetails


"""
Creates an embed for the game request message
"""


def game_info_embed(
    sending_to: UserId,
    title: str,
    game_status: GameStatus.Game,
    game_details: GameModuleDetails,
    footer_message: Optional[str] = None,
) -> discord.Embed:
    """Embed that gives information about a specific game.

    Args:
        sending_to (UserId): Id of user the embed will be sent to.
        title (str): Title of the embed.
        game_status (GameStatus.Game): Status object of the game being described.
        game_details (GameModuleDetails): Details object for the game module being played.
        footer_message (str, optional): Text that will be in footer.
            Defaults to None.

    Returns:
        discord.Embed: Complete game info embed
    """

    embed = discord.Embed(title=title)

    embed.add_field(name="Game", value=f"{game_status.game_module_name}")

    embed.add_field(
        name="Starting Player",
        value=f"{game_status.usernames[str(game_status.starting_user)]}",
    )

    # Gets list of other request users names
    # Won't list starting user or user embed will be sent to
    other_user_names = [
        game_status.usernames[other_users_ids]
        for other_users_ids in game_status.usernames.keys()
        if other_users_ids != sending_to
        and other_users_ids != game_status.starting_user
    ]

    # Adds other users names to embed
    if len(other_user_names):
        embed.add_field(name="Other Players", value=", ".join(other_user_names))

    # Adds game thumbnail to embed
    file = discord.File(game_details.thumbnail_file_path, filename="abc.png")
    embed.set_thumbnail(url=f"attachment://{file.filename}")

    if footer_message:
        embed.set_footer(text=footer_message)

    return embed


def game_summary_embed(
    winners: List[str],
    other_users: List[str],
    game_status: GameStatus.Game,
    ending_reason: Optional[str] = None,
) -> discord.Embed:
    """Summary of a finished game.

    Args:
        winners (List[str]): List of usernames of winners.
        other_users (List[str]): List of usernames of lossers.
        game_status (GameStatus.Game): Status of game being summarized
        ending_reason (str, optional): Text stating why game ended.
            Defaults to None.

    Returns:
        discord.Embed: Complete game summary embed.
    """

    embed = discord.Embed(title=f"Game of {game_status.game_module_name} is over!")

    winner_str = f"{', '.join(winners)}" if len(winners) else "None"
    embed.add_field(name="Winners", value=winner_str)
    embed.add_field(name="Other Players", value=f"{', '.join(other_users)}")

    if ending_reason:
        embed.set_footer(text=ending_reason)

    return embed


def game_list_embed(
    sending_to: UserId, is_active: bool, games_details: Dict[GameId, GameStatus.Game]
) -> discord.Embed:
    """Lists games a user is in.

    Args:
        sending_to (UserId): Id of user embed will be sent to.
        is_active (bool): Whether the games to be listed are ongoing.
        games_details (Dict[GameId, GameStatus.Game]): Dict with keys that are ids
            of the games to be listed with the value being the status of the game.

    Returns:
        discord.Embed: Complete game list embed.
    """

    games_type = "Active Games" if is_active else "Queued Games"

    embed = discord.Embed(title=(games_type))

    if len(games_details.keys()):
        for game_id, game_details in games_details.items():
            embed.add_field(
                name=game_description_string(game_details, sending_to),
                value=f"id: {game_id}",
            )
    else:
        embed.description = "No " + games_type.lower()

    return embed
