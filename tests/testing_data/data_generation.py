"""Contains functions for generating fake data"""

import random
import string
from typing import Literal

from data_wrappers.game_status import GameStatus


def create_game_id():
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


def create_fake_game_status(
    state: Literal[0, 1, 2],
    game_module_name,
    starting_user,
    user_count,
    pending_user_count,
):
    """Creates fake game status"""

    all_users = []
    pending_users = []
    usernames = {}
    for i in range(user_count):
        usernames[str(i)] = f"User {i}"
        all_users.append(i)
        if i < pending_user_count:
            pending_users.append(i)

    return GameStatus.Game(
        state=state,
        game_module_name=game_module_name,
        starting_user=starting_user,
        all_users=all_users,
        pending_users=pending_users,
        usernames=usernames,
    )
