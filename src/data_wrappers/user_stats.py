"""Contains the UserStats class used to store stats about users and games"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, cast

from dotenv import load_dotenv
from psycopg import IntegrityError
from psycopg_pool import AsyncConnectionPool

from data_types import GameResult, UserId

load_dotenv()


class UserStats:
    """API wrapper for db that stores info about users and games.

    The stored_game_id doesn't follow the same format as the regular game_id used throughout
        the rest of the project. This is because because it's more space-efficient and
        practical to use a smaller serial integer for the ID when storing data long-term.
    """

    __conn_pool = AsyncConnectionPool(
        f"{os.getenv('POSTGRES_URI')}", open="pytest" not in sys.modules.keys()
    )

    @dataclass
    class StoredUser:
        """Info about user.

        Attributes:
            user_id (int): Id of user.
            subscritption_start_date (datetime, optional): Date user's
                subscription started.
            subscription_end_date (datetime, optional): Date user's
                subscription ends.
            date_added (datetime): Date user was added to db.
        """

        user_id: int
        subscritption_start_date: Optional[datetime]
        subscription_end_date: Optional[datetime]
        date_added: datetime

    @dataclass
    class StoredGame:
        """Info about a past game.

        Attributes:
            stored_game_id (int): Id of game in db. Different from game_id format
                used in the rest of the project to refer to games.
            game_type (str): Type of game/name of game package.
            end_date (datetime): Date the game ended.
        """

        stored_game_id: int
        game_type: str
        end_date: datetime

    @dataclass
    class GameOutcome:
        """Info about game outcome of stored game.

        Attributes:
            user_id (UserId): Id of user who this outcome relates to.
            stored_game_id (int): Id of game this outcome relates to. Different
                from game_id format used in the rest of the project to refer
                to games.
            won (bool): True if user won game.
            tied (bool): True if user tied game.
        """

        user_id: UserId
        stored_game_id: int
        won: bool
        tied: bool

    @staticmethod
    async def __add_users(user_ids: List[Tuple[UserId]]) -> None:
        """Adds user to db if they don't already exist"""

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(
                    """
                    INSERT INTO discord_user (id)
                    VALUES (%s)
                    ON CONFLICT DO NOTHING
                    """,
                    user_ids,
                )

            await conn.commit()

    @staticmethod
    async def add_game(
        game_type: str, end_date: datetime, users: List[Tuple[UserId, GameResult]]
    ) -> int:
        """Adds a game to the db.

        Args:
            game_type (str): Type of game/name of game package.
            end_date (datetime): Date the game ended.
            users (list[(UserId, GameResult)]): List of tuples of user_ids
                and whether they won, lost, or tied.

        Returns:
            Stored id of the game added.
        """

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO game (game_type, end_date)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (game_type, end_date),
                )

                await conn.commit()

                stored_game_id = cast(Tuple[int], await cur.fetchone())[0]

                reran = False
                while True:
                    try:
                        await cur.executemany(
                            """
                            INSERT INTO game_outcome (user_id, game_id, won, tied)
                            VALUES (%s, %s, %s, %s)
                            """,
                            [
                                (
                                    user[0],
                                    stored_game_id,
                                    user[1] == GameResult.WON,
                                    user[1] == GameResult.TIED,
                                )
                                for user in users
                            ],
                        )

                    # Will raise if users not in db so add them and try again
                    except IntegrityError:
                        await conn.rollback()

                        if reran:
                            raise

                        await UserStats.__add_users([(user[0],) for user in users])
                        reran = True
                        continue

                    break

                await conn.commit()

        return stored_game_id

    @staticmethod
    async def get_user(user_id: UserId) -> Optional[StoredUser]:
        """Gets info about a user if it exists.

        Args:
            user_id (UserId): Id of user to get info about.

        Returns:
            StoredUser, optional: Stored user object of requested user.
        """

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, subscription_start_date, subscription_end_date, date_added
                    FROM discord_user
                    WHERE id = %s
                    """,
                    (user_id,),
                )

                user_tuple = await cur.fetchone()

        return UserStats.StoredUser(*user_tuple) if user_tuple else None

    @staticmethod
    async def recent_games(
        user_id: UserId,
        num_games: int = 1,
    ) -> List[Tuple[StoredGame, GameOutcome]]:
        """Gets the most recent game packages played by a user.

        Args:
            user_id (UserId): Id of user to get recent games for.
            num_games (int, optional): Number of games to return.
                Defaults to 1.

        Returns:
            List[(StoredGame, GameOutcome)]: List of tuples of stored games
                and the game outcome for the user in order of most recent
                to least recent.
        """

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT game.id, game.game_type, game.end_date, game_outcome.user_id, game_outcome.won, game_outcome.tied
                    FROM game_outcome
                    JOIN game ON game.id = game_outcome.game_id
                    WHERE game_outcome.user_id = %s
                    ORDER BY game.end_date DESC
                    """,
                    (user_id,),
                )

                return [
                    (
                        UserStats.StoredGame(*recentGameData[0:3]),
                        UserStats.GameOutcome(
                            recentGameData[3],
                            recentGameData[0],
                            recentGameData[4],
                            recentGameData[5],
                        ),
                    )
                    for recentGameData in await cur.fetchmany(num_games)
                ]

    @staticmethod
    async def most_played_games(
        user_id: UserId, num_games_returned: int = 1
    ) -> List[Tuple[str, int]]:
        """Returns the type of game/game package the user has played the most.

        Args:
            user_id (UserId): Id of user to get the most played game for.
            num_games_returned (int, optional): Number of types of games to return.
                Defaults to 1.

        Returns:
            List[(str, int)]: List of tuples of game type and number of times
                played in order of most to least played. tie is broken by game
                type in descending order.
        """

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT game.game_type, COUNT(*)
                    FROM game_outcome
                    JOIN game ON game.id = game_outcome.game_id
                    WHERE game_outcome.user_id = %s
                    GROUP BY game.game_type
                    ORDER BY COUNT(game.game_type) DESC,
                    game.game_type DESC
                    """,
                    (user_id,),
                )

                return await cur.fetchmany(num_games_returned)

    @staticmethod
    async def most_played_with_users(
        user_id: UserId, num_users_returned: int = 1
    ) -> List[Tuple[UserId, int]]:
        """Returns the users the user has played with the most.

        Args:
            user_id (UserId): Id of user to get most played with users for.
            num_users_returned (int, optional): Number of the most played with
                users to return. Defaults to 1.

        Returns:
            List[UserId]: List of user ids of the most played with users in order
                of most to least played with. Tie is broken by user_id in descending
                order.
        """

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id, COUNT(user_id)
                    FROM game_outcome
                    JOIN (
                        SELECT DISTINCT game_id
                        FROM game_outcome
                        WHERE user_id = %s
                    ) AS user_games ON game_outcome.game_id = user_games.game_id
                    WHERE user_id != %s
                    GROUP BY user_id
                    ORDER BY COUNT(user_id) DESC,
                    user_id DESC
                    """,
                    (user_id, user_id),
                )

                return [
                    (user[0], user[1])
                    for user in await cur.fetchmany(num_users_returned)
                ]

    @staticmethod
    async def delete_user(user_id: UserId) -> bool:
        """Deletes user from db.

        Args:
            user_id (UserId): Id of user to delete.

        Returns:
            bool: True if user was deleted, False if user did not exist.
        """

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM discord_user WHERE id = %s RETURNING id",
                    (user_id,),
                )

                await conn.commit()

                return bool(await cur.fetchone())

    @staticmethod
    async def clear_isolated_games() -> None:
        """Deletes games from db that have no outcomes"""

        async with UserStats.__conn_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM game
                    WHERE id NOT IN (
                        SELECT DISTINCT game_id
                        FROM game_outcome
                    )
                    """
                )
                await conn.commit()
