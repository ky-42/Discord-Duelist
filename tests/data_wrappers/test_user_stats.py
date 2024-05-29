import asyncio
import os
import random
from ctypes import cast
from datetime import datetime, timedelta
from random import choices, randint
from typing import List, Optional, Tuple

import psycopg
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from hypothesis import given
from hypothesis import strategies as st
from psycopg.sql import SQL, Identifier

from data_types import GameResult, UserId
from data_wrappers.user_stats import UserStats
from tests.testing_data.data_generation import gen_game_id, user_ids

pytestmark = pytest.mark.asyncio(scope="module")

load_dotenv()
conn = psycopg.connect(f"{os.getenv('POSTGRES_URI')}")

discord_user_table = "discord_user"
game_table = "game"
game_outcome_table = "game_outcome"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def open_pool():
    await UserStats._UserStats__conn_pool.open()


@pytest.fixture(scope="function", autouse=True)
def clear_tables():
    with conn.cursor() as cur:
        cur.execute(SQL("DELETE FROM {}").format(Identifier(discord_user_table)))
        cur.execute(SQL("DELETE FROM {}").format(Identifier(game_table)))
        cur.execute(SQL("DELETE FROM {}").format(Identifier(game_outcome_table)))

        conn.commit()

    yield

    with conn.cursor() as cur:
        cur.execute(SQL("DELETE FROM {}").format(Identifier(discord_user_table)))
        cur.execute(SQL("DELETE FROM {}").format(Identifier(game_table)))
        cur.execute(SQL("DELETE FROM {}").format(Identifier(game_outcome_table)))

        conn.commit()


# ------


@pytest.fixture(scope="function")
def add_test_user() -> UserId:
    return get_test_users(1)[0]


def get_test_users(user_count: int = 1) -> List[UserId]:
    """Adds a test user to the database"""

    added_ids = []

    starting_user_id = randint(1, 100000)

    with conn.cursor() as cur:
        for user_id_offset in range(user_count):
            cur.execute(
                SQL("INSERT INTO {} (id) VALUES (%s)").format(
                    Identifier(discord_user_table)
                ),
                (starting_user_id + user_id_offset,),
            )
            added_ids.append(starting_user_id + user_id_offset)

        conn.commit()

    return added_ids


def add_test_game(
    game_type: str = "Testing_Game",
    end_date: Optional[datetime] = None,
) -> Tuple[int, datetime]:
    """Adds a test game to the database and returns the game id and end date"""

    if end_date is None:
        end_date = datetime.now()

    with conn.cursor() as cur:
        cur.execute(
            SQL(
                "INSERT INTO {} (game_type, end_date) VALUES (%s, %s) RETURNING id"
            ).format(Identifier(game_table)),
            (
                game_type,
                end_date,
            ),
        )

        conn.commit()

        stored_game_id = cur.fetchone()

        if stored_game_id is not None:
            return (stored_game_id[0], end_date)
        raise ValueError("Game was not added to the database")


def add_test_outcome(
    stored_game_id: int, user_id: UserId, won: bool = True, tied: bool = False
) -> None:
    """Adds a test outcome to the database"""

    with conn.cursor() as cur:
        cur.execute(
            SQL(
                "INSERT INTO {} (game_id, user_id, won, tied) VALUES (%s, %s, %s, %s)"
            ).format(Identifier(game_outcome_table)),
            (
                stored_game_id,
                user_id,
                won,
                tied,
            ),
        )

        conn.commit()


# ------


@given(
    user_ids=st.lists(
        st.tuples(st.integers(min_value=0, max_value=1000000)), min_size=1, max_size=10
    )
)
async def test_add_user(user_ids: List[Tuple[UserId]]):
    await UserStats._UserStats__add_users(user_ids)  # type: ignore

    with conn.cursor() as cur:
        for user_id in user_ids:
            cur.execute(
                SQL("SELECT * FROM {} WHERE id = %s").format(
                    Identifier(discord_user_table)
                ),
                user_id,
            )

            assert cur.fetchone()[0] in [user_id_tuple[0] for user_id_tuple in user_ids]


async def test_no_users_added():
    await UserStats._UserStats__add_users([])  # type: ignore

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM discord_user")

        assert cur.fetchone() is None


async def test_add_game():

    game_type = "Testing_Game"
    end_date = datetime.now()
    users = [1, 2, 3]

    await UserStats.add_game(
        game_type,
        end_date,
        [(user_id, GameResult.WON) for user_id in users],
    )

    with conn.cursor() as cur:
        cur.execute(
            SQL("SELECT id FROM {} WHERE game_type = %s").format(
                Identifier(game_table)
            ),
            (game_type,),
        )

        stored_game_id = cur.fetchone()[0]

        assert stored_game_id is not None

        cur.execute(
            SQL("SELECT user_id, won FROM {} WHERE game_id = %s").format(
                Identifier(game_outcome_table)
            ),
            (stored_game_id,),
        )

        # Makes sure game outcome was added for each user
        result = cur.fetchmany(len(users))
        print(result)
        assert {user_and_result[0] for user_and_result in result} <= set(users)
        assert all(user_and_result[1] == True for user_and_result in result)


async def test_get_user(add_test_user: UserId):
    user_status = await UserStats.get_user(add_test_user)

    assert user_status

    assert (
        not user_status.subscription_end_date
        and not user_status.subscritption_start_date
        and user_status.user_id == add_test_user
    )

    current_datetime = datetime.now()
    end_datetime = current_datetime.replace(month=current_datetime.month + 1)

    with conn.cursor() as cur:
        cur.execute(
            SQL(
                "UPDATE {} SET subscription_start_date = %s, subscription_end_date = %s WHERE id = %s"
            ).format(Identifier(discord_user_table)),
            (current_datetime, end_datetime, add_test_user),
        )

        conn.commit()

    user_status = await UserStats.get_user(add_test_user)

    assert (
        user_status is not None
        and user_status.subscritption_start_date == current_datetime
        and user_status.subscription_end_date == end_datetime
    )


async def test_recent_games(add_test_user):
    most_recent_game_count = 4
    total_game_count = 3

    end_date = (x := datetime.now()).replace(year=x.year - 1)

    # [Wins, Ties, Losses]
    for i in range(most_recent_game_count + total_game_count):

        stored_game_id, _ = add_test_game(end_date=end_date)
        add_test_outcome(
            stored_game_id=stored_game_id, user_id=add_test_user, won=True, tied=False
        )

        # Adds games on different days so getting the most recent games works
        end_date = end_date + timedelta(days=1)

    recent_games = await UserStats.recent_games(
        add_test_user, num_games=most_recent_game_count
    )

    assert len(recent_games) == most_recent_game_count
    assert all([game[1].won for game in recent_games])

    most_recent_game = await UserStats.recent_games(add_test_user)

    assert len(most_recent_game) == 1
    assert all(game[1].won for game in recent_games)


async def test_recent_games_no_games(add_test_user: UserId):

    assert not len(await UserStats.recent_games(add_test_user))

    assert not len(await UserStats.recent_games(add_test_user, 10))


# @given(
#     game_list=st.lists(st.integers(min_value=1, max_value=6), min_size=30, max_size=50)
# )
async def test_most_played_games():
    game_list = [str(randint(1, 6)) for _ in range(50)]

    test_user = get_test_users(1)[0]

    for game in game_list:
        stored_game_id, _ = add_test_game(game_type=str(game))
        add_test_outcome(stored_game_id=stored_game_id, user_id=test_user)

    # Gets the count of each game
    game_counts = [(i, game_list.count(i)) for i in set(game_list)]
    # Ties are broken by the game id
    game_counts.sort(key=lambda game: (game[1], game[0]), reverse=True)

    most_played_game = await UserStats.most_played_games(test_user)
    assert most_played_game[0] == game_counts[0]

    num_games_to_get = randint(1, 6)
    most_played_games = await UserStats.most_played_games(
        test_user, num_games_returned=num_games_to_get
    )

    try:
        assert most_played_games == game_counts[:num_games_to_get]
    except IndexError:
        assert most_played_games == game_counts


async def test_get_most_played_games_no_games(add_test_user):

    assert not len(await UserStats.most_played_games(add_test_user))

    assert not len(await UserStats.most_played_games(add_test_user, 10))


# @given(
#     user_count=st.integers(min_value=5, max_value=20),
#     play_count=st.integers(min_value=1, max_value=100),
# )
async def test_get_most_played_with():

    test_user = get_test_users(4)

    main_player = test_user[0]
    del test_user[0]

    # Stores how many times each player has played with the main player
    player_play_count = {user_id: 0 for user_id in test_user}

    (game_one, _) = add_test_game()
    (game_two, _) = add_test_game()
    (game_three, _) = add_test_game()

    add_test_outcome(stored_game_id=game_one, user_id=main_player)
    add_test_outcome(stored_game_id=game_two, user_id=main_player)
    add_test_outcome(stored_game_id=game_three, user_id=main_player)

    add_test_outcome(stored_game_id=game_one, user_id=test_user[0])
    add_test_outcome(stored_game_id=game_two, user_id=test_user[0])
    add_test_outcome(stored_game_id=game_three, user_id=test_user[0])

    add_test_outcome(stored_game_id=game_one, user_id=test_user[1])
    add_test_outcome(stored_game_id=game_two, user_id=test_user[1])

    most_played_with = await UserStats.most_played_with_users(main_player)

    assert most_played_with[0] == (test_user[0], 3)

    most_played_with = await UserStats.most_played_with_users(
        main_player, num_users_returned=3
    )

    assert most_played_with == [(test_user[0], 3), (test_user[1], 2)]


async def test_most_played_with_no_games(add_test_user: UserId):
    assert not len(await UserStats.most_played_with_users(add_test_user))

    assert not len(await UserStats.most_played_with_users(add_test_user, 10))


async def test_delete_user(add_test_user: UserId):
    assert await UserStats.delete_user(add_test_user)

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM discord_user WHERE id = %s", (add_test_user,))

        assert cur.fetchone() is None


async def test_delete_user_no_user(add_test_user: UserId):
    assert not await UserStats.delete_user(1)

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM discord_user WHERE id = %s", (add_test_user,))

        assert cur.fetchone() is not None


async def test_clear_games(add_test_user):
    game_id_one, _ = add_test_game()
    add_test_game()
    add_test_outcome(game_id_one, add_test_user)  # type: ignore

    await UserStats.clear_isolated_games()

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM game")

        assert cur.fetchone() == (game_id_one,)
        assert cur.fetchone() is None
