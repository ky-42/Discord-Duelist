from datetime import datetime
from random import choices, randint
from typing import List, Tuple

import psycopg
import pytest
from hypothesis import given
from hypothesis import strategies as st
from psycopg.sql import SQL, Identifier

from data_types import UserId
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
    end_date: datetime = None,
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

        return (cur.fetchone()[0], end_date)


def add_test_outcome(
    db_game_id: int, user_id: UserId, won: bool = True, tie: bool = False
) -> None:
    """Adds a test outcome to the database"""

    with conn.cursor() as cur:
        cur.execute(
            SQL(
                """
                INSERT INTO {} (game_id, user_id, won, tie)
                VALUES (%s, %s, %s, %s)
                """
            ).format(Identifier(game_outcome_table)),
            (
                db_game_id,
                user_id,
                won,
                tie,
            ),
        )

        cur.commit()


async def test_add_user(user_id: UserId):
    await UserStats.add_user(user_id)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM {} WHERE id = %s",
            SQL(discord_user_table),
            (user_id,),
        )
        cur.commit()

        result = cur.fetchone()

    assert result is not None and result[0] == user_id and result[1] == 0


async def test_is_supporter(add_test_user: UserId):
    is_supporter = await UserStats.is_supporter(add_test_user)

    assert not is_supporter

    with conn.cursor() as cur:
        cur.execute(
            SQL(
                """
                UPDATE {} SET subscription_start_date = %s,
                subscription_end_date = %s WHERE id = %s
                """
            ).format(Identifier(discord_user_table)),
            (
                datetime.now(),
                datetime.now().replace(day=datetime.now().day + 1),
                add_test_user,
            ),
        )

        conn.commit()

    assert await UserStats.is_supporter(add_test_user)


async def test_get_supporter_status(add_test_user: UserId):
    subscription_start, subscription_end = await UserStats.get_supporter_status(
        add_test_user
    )

    assert not subscription_start and not subscription_end

    current_datetime = datetime.now()
    end_datetime = current_datetime.replace(month=current_datetime.month + 1)

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE %s SET supporter = 1, subscription_start_date = %s, subscription_end_date = %s WHERE id = %s",
            (discord_user_table, current_datetime, end_datetime, add_test_user),
        )

        conn.commit()

    subscription_start, subscription_end = await UserStats.get_supporter_status(
        add_test_user
    )

    assert subscription_start == current_datetime and subscription_end == end_datetime


@given(
    total_game_count=st.integers(min_value=5, max_value=150),
    games_in_last_days=st.integers(min_value=1, max_value=10),
)
async def test_get_game_outcomes(
    add_test_user: UserId, total_game_count: int, most_recent_game_count: int
):
    end_date = datetime.now().replace(year=end_date.year - 1)

    # [Wins, Ties, Losses]
    all_outcomes = [0, 0, 0]
    most_recent_games = [0, 0, 0]
    for i in range(most_recent_game_count + total_game_count):
        game_outcome = randint(0, 2)
        won = game_outcome == 0
        tie = game_outcome == 1

        all_outcomes[game_outcome] += 1

        if i >= most_recent_game_count:
            most_recent_games[game_outcome] += 1

        db_game_id, _ = add_test_game(end_date=end_date)
        add_test_outcome(
            db_game_id=db_game_id, game_user_id=add_test_user, won=won, tie=tie
        )

        # Adds games on different days so getting the most recent games works
        end_date = end_date.replace(day=end_date.day + 1)

    wins, ties, losses = await UserStats.get_game_outcomes(
        add_test_user, most_recent_game_count
    )

    assert (
        wins == most_recent_games[0]
        and ties == most_recent_games[1]
        and losses == most_recent_games[2]
    )

    wins, ties, losses = await UserStats.get_game_outcomes(add_test_user)

    assert (
        wins == all_outcomes[0]
        and ties == all_outcomes[1]
        and losses == all_outcomes[2]
    )


async def test_get_game_outcomes_no_games(add_test_user: UserId):
    wins, ties, losses = await UserStats.get_game_outcomes(add_test_user)

    assert wins == 0 and ties == 0 and losses == 0

    wins, ties, losses = await UserStats.get_game_outcomes(add_test_user, 10)

    assert wins == 0 and ties == 0 and losses == 0


@given(
    game_list=st.lists(st.integers(min_value=1, max_value=6), min_size=30, max_size=50)
)
async def test_get_most_played_game(add_test_user: UserId, game_list: List[int]):
    for game in game_list:
        db_game_id, _ = add_test_game(game_type=str(game))
        add_test_outcome(db_game_id=db_game_id, game_user_id=add_test_user)

    # Gets the count of each game
    game_counts = [(i, game_list.count(i)) for i in set(game_list)]
    # Ties are broken by the game id
    game_counts.sort(key=lambda game: (game[1], game[0]), reverse=True)

    most_played_game = await UserStats.get_most_played_game(add_test_user)
    assert most_played_game == game_counts[0][0]

    top_x = randint(1, 6)
    most_played_games = await UserStats.get_most_played_game(add_test_user, top_x)

    try:
        assert most_played_games == [i[0] for i in game_counts[:top_x]]
    except IndexError:
        assert most_played_games == [i[0] for i in game_counts]


async def test_get_most_played_games_no_games(add_test_user: UserId):
    assert not len(await UserStats.get_most_played_game(add_test_user))

    assert not len(await UserStats.get_most_played_game(add_test_user, 10))


@given(play_count=st.integers(min_value=1, max_value=100))
@pytest.mark.parametrize("add_test_user", 10, indirect=True)
async def test_get_most_played_with(add_test_user: List[UserId], play_count: int):

    main_player = add_test_user[0]
    del add_test_user[0]

    # Stores how many times each player has played with the main player
    other_player_play_count = {(user_id, 0) for user_id in add_test_user}

    for _ in play_count:
        db_game_id, _ = add_test_game()

        for player_with_user in choices(add_test_user, k=randint(2, 6)):
            add_test_outcome(db_game_id=db_game_id, game_user_id=player_with_user)
            other_player_play_count[player_with_user] += 1

    # Ties are broken by the user id
    other_player_play_count = sorted(
        other_player_play_count, key=lambda game: (game[1], game[0]), reverse=True
    )

    most_played_with = await UserStats.get_most_played_with_user(main_player)

    assert most_played_with == other_player_play_count[0]

    most_played_with = await UserStats.get_most_played_with_user(main_player, 3)

    assert most_played_with == other_player_play_count[:3]


async def test_get_most_played_with_no_games(add_test_user: UserId):
    assert not len(await UserStats.get_most_played_with_user(add_test_user))

    assert not len(await UserStats.get_most_played_with_user(add_test_user, 10))


@given(play_count=st.integers(min_value=1, max_value=20))
async def test_get_last_games(add_test_user: UserId, play_count: int):
    game_order = []
    end_date = datetime.now().replace(day=end_date.day - 40)

    for _ in play_count:
        db_game_id, _ = add_test_game(end_date=end_date)
        add_test_outcome(db_game_id=db_game_id, game_user_id=add_test_user)

        game_order.append(db_game_id)

        end_date = end_date.replace(day=end_date.day + 1)

    last_game = await UserStats.get_last_games(add_test_user)

    assert last_game.id == game_order[0]

    last_x_games = await UserStats.get_last_games(add_test_user, 5)

    assert [i.id for i in last_x_games] == game_order[-5:]


async def test_get_most_played_with_no_games(add_test_user: UserId):
    assert not len(await UserStats.get_last_games(add_test_user))

    assert not len(await UserStats.get_last_games(add_test_user, 10))


@pytest.mark.parametrize("add_test_user", 3, indirect=True)
async def test_add_game(add_test_user: List[UserId]):
    game_type = "find_me"
    await UserStats.add_game(game_type, 1000, datetime.now(), add_test_user)

    with conn.cursor() as cur:
        cur.execute(
            SQL("SELECT * FROM {} WHERE game_type = %s RETURNING game_id").format(
                Identifier(game_table)
            ),
            (game_type,),
        )

        db_game_id = cur.fetchone()

        assert db_game_id is not None

        cur.execute(
            SQL("SELECT * FROM {} WHERE game_id = %s RETURNING user_id").format(
                Identifier(game_outcome_table)
            ),
            (db_game_id,),
        )

        # Makes sure game outcome was added for each user
        assert cur.fetchmany(3) == add_test_user


async def test_delete_user(add_test_user: UserId):
    await UserStats.delete_user(add_test_user)

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (add_test_user,))

        assert cur.fetchone() is None


async def test_delete_user_no_user():
    with pytest.raises(UserNotFound):
        await UserStats.delete_user(1)


async def test_clear_games():
    game_id_one, _ = add_test_game()
    game_id_two, _ = add_test_game()
    add_test_outcome(game_id_one, 1)

    await UserStats.clear_games()

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM game RETURNING game_id")

        assert cur.fetchone() is game_id_two
        assert cur.fetchone() is None
