"""Contains the UserStats class used to store stats about users and games"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from data_types import GameResult, UserId


class UserStats:
    """API wrapper for db that stores info about users and games.

    The stored_game_id doesn't follow the same format as the regular game_id used in the
        rest of the project. This is because because it's more space-efficient and practical
        to use a smaller serial integer for the ID when storing data long-term.
    """

    @dataclass
    class StoredGame:
        """Info about game in long-term storage.

        Attributes:
            stored_game_id (int): Id of game in db. Different from game_id format
                used in the rest of the project to refer to games.
            game_type (str): Type of game/name of game module.
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
    async def __add_user(user_id: UserId) -> None:
        """Adds user to db if they don't already exist"""

        pass

    @staticmethod
    async def add_game(
        game_type: str, end_date: datetime, users: List[Tuple[UserId, GameResult]]
    ) -> int:
        """Adds a game to the db.

        Args:
            game_type (str): Type of game/name of game module.
            end_date (datetime): Date the game ended.
            users (list[(UserId, GameResult)]): List of tuples of user_ids
                and whether they won, lost, or tied.

        Returns:
            Stored id of the game added.
        """

        pass

    @staticmethod
    async def supporter_status(user_id: UserId) -> Optional[Tuple[datetime, datetime]]:
        """Gets start and end date of supporter status if it exists.

        Args:
            user_id (UserId): Id of user to check supporter status for.

        Returns:
            (datetime, datetime), optional: Start and end date of supporter status.
        """

        pass

    @staticmethod
    async def recent_games(
        user_id: UserId,
        num_games_returned: int = 1,
    ) -> List[Tuple[StoredGame, GameOutcome]]:
        """Gets the most recent games played by a user.

        Args:
            user_id (UserId): Id of user to get recent games for.
            num_outcomes_returned (int, optional): Number of games to return.
                Defaults to 1.

        Returns:
            List[(StoredGame, GameOutcome)]: List of tuples of stored games
                and the game outcome for the user in order of most recent
                to least recent.
        """

        pass

    @staticmethod
    async def most_played_games(
        user_id: UserId, num_games_returned: int = 1
    ) -> List[Tuple[str, int]]:
        """Returns the type of game/game module the user has played the most.

        Args:
            user_id (UserId): Id of user to get the most played game for.
            num_games_returned (int, optional): Number of types of games to return.
                Defaults to 1.

        Returns:
            List[(str, int)]: List of tuples of game type and number of times
                played in order of most to least played.
        """

        pass

    @staticmethod
    async def most_played_with_users(
        user_id: UserId, num_users_returned: int = 1
    ) -> List[UserId]:
        """Returns the users the user has played with the most.

        Args:
            user_id (UserId): Id of user to get most played with users for.
            num_users_returned (int, optional): Number of the most played with
                users to return. Defaults to 1.

        Returns:
            List[UserId]: List of user ids of the most played with users in order
                of most to least played with.
        """

        pass

    @staticmethod
    async def delete_user(user_id: UserId) -> bool:
        """Deletes user from db.

        Args:
            user_id (UserId): Id of user to delete.

        Returns:
            bool: True if user was deleted, False if user did not exist.
        """

        pass

    @staticmethod
    async def clear_isolated_games() -> None:
        """Deletes games from db that have no outcomes"""

        pass
