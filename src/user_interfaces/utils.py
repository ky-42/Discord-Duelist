from typing import Optional

from data_types import GameId, UserId
from data_wrappers.game_status import GameStatus


def game_description_string(
    game_details: GameStatus.Game, asking_user: UserId, game_id: Optional[GameId] = None
) -> str:
    """
    Creates a string that describes a game to a user
    """

    # Creates a list of other users in the games
    user_names = ", ".join(
        [
            name.capitalize()
            for user_id, name in game_details.player_names.items()
            if asking_user != user_id
        ]
    )

    main_string = f"{game_details.game.capitalize()}  with {user_names}"

    if game_id:
        main_string += f" ({game_id})"

    return main_string
