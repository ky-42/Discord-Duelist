from __future__ import annotations

from typing import TYPE_CHECKING

import discord

# Stops circular import
if TYPE_CHECKING:
    from data_wrappers.game_status import GameStatus
    from games.utils import GameDetails


def create_confirm_embed(
    player_id: int, game_state: GameStatus.Game, game_details: GameDetails
) -> discord.Embed:
    """
    Creates an embed for the game request message
    """

    message_embed = discord.Embed(
        title=f"{game_state.player_names[str(game_state.starting_player)]} wants to play a game!",
    )

    message_embed.add_field(name="Game", value=f"{game_state.game}", inline=True)

    # Gets list of other request users names
    other_player_names = [
        game_state.player_names[other_players_ids]
        for other_players_ids in game_state.player_names.keys()
        if other_players_ids != player_id
        and other_players_ids != game_state.starting_player
    ]

    # Adds other players names to embed
    if len(other_player_names):
        message_embed.add_field(
            name="Other Players", value=", ".join(other_player_names), inline=True
        )

    # Adds game thumbnail to embed
    file = discord.File(game_details.thumbnail_file_path, filename="abc.png")
    message_embed.set_thumbnail(url=f"attachment://{file.filename}")

    # Adds bet to embed
    if game_state.bet:
        message_embed.add_field(name="Bet", value=game_state.bet, inline=False)

    return message_embed