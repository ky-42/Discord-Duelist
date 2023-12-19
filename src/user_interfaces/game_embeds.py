from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

import discord

from data_types import GameId, UserId
from user_interfaces.utils import game_description_string

# Stops circular import
if TYPE_CHECKING:
    from data_wrappers.game_status import GameStatus
    from games.utils import GameModuleDetails


def game_info_embed(
    sending_to: int,
    title: str,
    game_state: GameStatus.Game,
    game_details: GameModuleDetails,
    expire_message: Optional[str] = None,
) -> discord.Embed:
    """
    Creates an embed for the game request message
    """

    embed = discord.Embed(title=title)

    embed.add_field(name="Game", value=f"{game_state.game_module_name}", inline=True)

    embed.add_field(
        name="Starting Player",
        value=f"{game_state.player_names[str(game_state.starting_player)]}",
    )

    # Gets list of other request users names
    other_player_names = [
        game_state.player_names[other_players_ids]
        for other_players_ids in game_state.player_names.keys()
        if other_players_ids != sending_to
        and other_players_ids != game_state.starting_player
    ]

    # Adds other players names to embed
    if len(other_player_names):
        embed.add_field(
            name="Other Players", value=", ".join(other_player_names), inline=True
        )

    # Adds game thumbnail to embed
    file = discord.File(game_details.thumbnail_file_path, filename="abc.png")
    embed.set_thumbnail(url=f"attachment://{file.filename}")

    if expire_message:
        embed.set_footer(text=expire_message)

    return embed


def game_summary_embed(
    winners: List[str],
    other_players: List[str],
    game_status: GameStatus.Game,
    ending_reason: Optional[str] = None,
) -> discord.Embed:
    """
    Used when a game ends
    """

    embed = discord.Embed(title=f"Game of {game_status.game_module_name} is over!")

    winner_str = f"{', '.join(winners)}" if len(winners) else "None"
    embed.add_field(name="Winners", value=winner_str)
    embed.add_field(name="Other Players", value=f"{', '.join(other_players)}")

    if ending_reason:
        embed.set_footer(text=ending_reason)

    return embed


def game_list_embed(
    sending_to: UserId, is_active: bool, games_details: Dict[GameId, GameStatus.Game]
) -> discord.Embed:
    """
    Creates an embed that list the games a user is in
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
