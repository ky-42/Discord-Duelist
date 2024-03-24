from datetime import datetime
from random import choices, randint
from typing import List, Optional, Tuple

import psycopg
import pytest
from hypothesis import given
from hypothesis import strategies as st
from psycopg.sql import SQL, Identifier

from data_types import GameResult, UserId
from data_wrappers.user_stats import UserStats
from exceptions import UserNotFound
from tests.testing_data.data_generation import gen_game_id, user_id

conn = psycopg.connect()


discord_user_table = "discord_user_test"
game_table = "game_test"
game_outcome_table = "game_outcome_test"


@pytest.fixture(scope="module", autouse=True)
def setup_test_tables():
    """Creates and drops test tables"""

    with conn.cursor() as cur:
        # Creates test tables
        cur.execute(
            SQL(
                """
                CREATE TABLE {}
                AS SELECT * FROM discord_user WITH NO DATA
                """,
            ).format(discord_user_table)
        )
        cur.execute(
            SQL(
                """
                CREATE TABLE {}
                AS SELECT * FROM game WITH NO DATA
                """,
            ).format(game_table)
        )
        cur.execute(
            SQL(
                """
                CREATE TABLE {}
                AS SELECT * FROM game_outcome WITH NO DATA
                """,
            ).format(game_outcome_table)
        )

        conn.commit()

    yield

    with conn.cursor() as cur:
        cur.execute(SQL("DROP TABLE %s").format(game_outcome_table))
        cur.execute(SQL("DROP TABLE %s").format(game_table))
        cur.execute(SQL("DROP TABLE %s").format(discord_user_table))

        conn.commit()


@pytest.fixture
def add_test_user(user_count: int = 1) -> UserId | List[UserId]:
    """Adds a test user to the database"""

    added_ids = []

    starting_user_id = randint(1, 100000)

    with conn.cursor() as cur:
        for user_id_offset in range(user_count):
            cur.execute(
                SQL("INSERT INTO {} (user_id) VALUES (%s)").format(
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
                """
                INSERT INTO {} (game_type, end_date)
                VALUES (%s, %s) RETURNING id
                """
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
                """
                INSERT INTO {} (game_id, user_id, won, tied)
                VALUES (%s, %s, %s, %s)
                """
            ).format(Identifier(game_outcome_table)),
            (
                stored_game_id,
                user_id,
                won,
                tied,
            ),
        )

        conn.commit()


async def test_add_user(user_id: UserId):
    await UserStats._UserStatus__add_user(user_id)  # type: ignore

    with conn.cursor() as cur:
        cur.execute(
            SQL("SELECT * FROM {} WHERE id = %s").format(discord_user_table),
            (user_id,),
        )

        conn.commit()

        result = cur.fetchone()

    assert (
        result is not None
        and result[0] == user_id
        and result[1] == None
        and result[2] == None
    )


@pytest.mark.parametrize("add_test_user", [2, 3, 4], indirect=True)
async def test_add_game(add_test_user: List[UserId]):
    game_type = "find_me"

    await UserStats.add_game(
        game_type,
        datetime.now(),
        [(user_id, GameResult.WON) for user_id in add_test_user],
    )

    with conn.cursor() as cur:
        cur.execute(
            SQL("SELECT * FROM {} WHERE game_type = %s RETURNING game_id").format(
                Identifier(game_table)
            ),
            (game_type,),
        )

        stored_game_id = cur.fetchone()

        assert stored_game_id is not None

        cur.execute(
            SQL("SELECT * FROM {} WHERE game_id = %s RETURNING (user_id, won)").format(
                Identifier(game_outcome_table)
            ),
            (stored_game_id,),
        )

        # Makes sure game outcome was added for each user
        result = cur.fetchmany(len(add_test_user))
        assert {user_and_result[0] for user_and_result in result} <= set(add_test_user)
        assert all(user_and_result[1] == GameResult.WON for user_and_result in result)


async def test_supporter_status(add_test_user: UserId):
    supporter_status = await UserStats.supporter_status(add_test_user)
    subscription_start, subscription_end = (
        supporter_status if supporter_status is not None else (None, None)
    )

    assert not subscription_start and not subscription_end

    current_datetime = datetime.now()
    end_datetime = current_datetime.replace(month=current_datetime.month + 1)

    with conn.cursor() as cur:
        cur.execute(
            SQL(
                """
                UPDATE {} SET supporter = 1, subscription_start_date = %s,
                subscription_end_date = %s WHERE id = %s
                """
            ).format(Identifier(discord_user_table)),
            (discord_user_table, current_datetime, end_datetime, add_test_user),
        )

        conn.commit()

    supporter_status = await UserStats.supporter_status(add_test_user)
    subscription_start, subscription_end = (
        supporter_status if supporter_status is not None else (None, None)
    )

    assert subscription_start == current_datetime and subscription_end == end_datetime


@given(
    total_game_count=st.integers(min_value=5, max_value=150),
    games_in_last_days=st.integers(min_value=1, max_value=10),
)
async def test_recent_games(
    add_test_user: UserId, total_game_count: int, most_recent_game_count: int
):
    end_date = (x := datetime.now()).replace(year=x.year - 1)

    # [Wins, Ties, Losses]
    for i in range(most_recent_game_count + total_game_count):

        stored_game_id, _ = add_test_game(end_date=end_date)
        add_test_outcome(
            stored_game_id=stored_game_id, user_id=add_test_user, won=True, tied=False
        )

        # Adds games on different days so getting the most recent games works
        end_date = end_date.replace(day=end_date.day + 1)

    recent_games = await UserStats.recent_games(
        add_test_user, num_games_returned=most_recent_game_count
    )

    assert len(recent_games) == most_recent_game_count
    assert all([game[1].won for game in recent_games])

    most_recent_game = await UserStats.recent_games(add_test_user)

    assert len(most_recent_game) == total_game_count
    assert all(game[1].won for game in recent_games)


async def test_recent_games_no_games(add_test_user: UserId):
    assert not len(await UserStats.recent_games(add_test_user))

    assert not len(await UserStats.recent_games(add_test_user, 10))


@given(
    game_list=st.lists(st.integers(min_value=1, max_value=6), min_size=30, max_size=50)
)
async def test_most_played_games(add_test_user: UserId, game_list: List[int]):
    for game in game_list:
        stored_game_id, _ = add_test_game(game_type=str(game))
        add_test_outcome(stored_game_id=stored_game_id, user_id=add_test_user)

    # Gets the count of each game
    game_counts = [(i, game_list.count(i)) for i in set(game_list)]
    # Ties are broken by the game id
    game_counts.sort(key=lambda game: (game[1], game[0]), reverse=True)

    most_played_game = await UserStats.most_played_games(add_test_user)
    assert most_played_game[0] == game_counts[0]

    num_games_to_get = randint(1, 6)
    most_played_games = await UserStats.most_played_games(
        add_test_user, num_games_returned=num_games_to_get
    )

    try:
        assert most_played_games == game_counts[:num_games_to_get]
    except IndexError:
        assert most_played_games == game_counts


async def test_get_most_played_games_no_games(add_test_user: UserId):
    assert not len(await UserStats.most_played_games(add_test_user))

    assert not len(await UserStats.most_played_games(add_test_user, 10))


@given(play_count=st.integers(min_value=1, max_value=100))
@pytest.mark.parametrize("add_test_user", [5, 10, 20], indirect=True)
async def test_get_most_played_with(add_test_user: List[UserId], play_count: int):

    main_player = add_test_user[0]
    del add_test_user[0]

    # Stores how many times each player has played with the main player
    player_play_count = {user_id: 0 for user_id in add_test_user}

    for _ in range(play_count):
        stored_game_id, _ = add_test_game()

        for player_with_user in choices(add_test_user, k=randint(2, 6)):
            add_test_outcome(stored_game_id=stored_game_id, user_id=player_with_user)
            player_play_count[player_with_user] += 1

    # Turn dict into a sorted list of tuples with form (user_id, play_count)
    # Ties are broken by the user id
    player_play_count = sorted(
        {(user_id, play_count) for user_id, play_count in player_play_count.items()},
        key=lambda game: (game[1], game[0]),
        reverse=True,
    )

    most_played_with = await UserStats.most_played_with_users(main_player)

    assert most_played_with[0] == player_play_count[0]

    most_played_with = await UserStats.most_played_with_users(
        main_player, num_users_returned=3
    )

    assert most_played_with == player_play_count[:3]


async def test_most_played_with_no_games(add_test_user: UserId):
    assert not len(await UserStats.most_played_with_users(add_test_user))

    assert not len(await UserStats.most_played_with_users(add_test_user, 10))


async def test_delete_user(add_test_user: UserId):
    assert await UserStats.delete_user(add_test_user)

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (add_test_user,))

        assert cur.fetchone() is None


async def test_delete_user_no_user(add_test_user: UserId):
    assert not await UserStats.delete_user(1)

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (add_test_user,))

        assert cur.fetchone() is not None


async def test_clear_games():
    game_id_one, _ = add_test_game()
    game_id_two, _ = add_test_game()
    add_test_outcome(game_id_one, 1)

    await UserStats.clear_isolated_games()

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM game RETURNING game_id")

        assert cur.fetchone() is game_id_two
        assert cur.fetchone() is None
