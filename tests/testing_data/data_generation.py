"""Contains functions for generating fake data"""

import random
import string
from typing import Literal

import pytest

from data_wrappers.game_status import GameStatus
from data_wrappers.user_status import UserStatus


@pytest.fixture
def game_id():
    """Generates a random game id"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


@pytest.fixture
def user_id():
    """Generates a random user id"""
    return random.randint(1, 100000)


def generate_game_status(
    state: Literal[0, 1, 2],
    game_module_name: str,
    user_count: int,
    pending_user_count: int,
):
    """Creates fake game status.

    User ids are the values from 0 to user_count - 1 with the usernames
    being "User 0" to "User {user_count - 1}".

    Starting user is user_count - 1.

    The pending users are the values from 0 to pending_user_count - 1.
    """

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
        starting_user=all_users[-1],
        all_users=all_users,
        pending_users=pending_users,
        usernames=usernames,
    )


def generate_user_status(
    active_games_count: int,
    queued_games_count: int,
    notifications_count: int = 0,
    has_notification_msg: bool = False,
    starting_game_id: int = 0,
):
    """Creates fake user status.

    The active games are the values from 0 to active_games_count - 1.

    The queued games are the values from active_games_count to:
        active_games_count + queued_games_count - 1

    The notifications are the values from 0 to notifications_count - 1

    If has_notification_msg is True, the notification_id is set to 0
    """

    return UserStatus.User(
        active_games=list(
            map(str, range(starting_game_id, starting_game_id + active_games_count))
        ),
        queued_games=list(
            map(
                str,
                range(
                    starting_game_id + active_games_count,
                    starting_game_id + queued_games_count + active_games_count,
                ),
            )
        ),
        notifications=list(map(str, range(notifications_count))),
        notification_id=None if not has_notification_msg else 0,
    )
