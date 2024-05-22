"""Contains functions for generating fake data"""

import random
import string

import pytest


@pytest.fixture
def game_id():
    """Generates a random game id"""

    return gen_game_id()


def gen_game_id():
    """Generates a random game id"""

    return "".join(
        random.choices(string.ascii_letters + string.digits + string.punctuation, k=8)
    )


@pytest.fixture
def user_ids():
    """Generates a random user id"""

    return random.randint(1, 100000)
