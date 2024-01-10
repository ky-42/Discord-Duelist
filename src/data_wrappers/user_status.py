"""Contains the UserStatus class which keeps track of the status of users"""

from dataclasses import asdict, dataclass
from typing import List, Optional, Set

import redis
import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client

from data_types import GameId, MessageId, UserId
from exceptions import GameNotFound, UserNotFound

from .utils import pipeline_watch


class UserStatus:
    """API wrapper for db which handles the status of users.

    All data in the db is in the key:value form:
        UserId: UserState
    """

    # Redis db number and redis connection pool
    __db_number = 2
    __pool = redis_sync.Redis(db=__db_number)

    __max_active_games = 6
    __max_queued_games = 6

    @dataclass
    class User:
        """Dataclass for storing user status.

        Attributes:
            active_games (List[GameId]): List of ids of games the user is current
                playing.
            queued_games (List[GameId]): List of ids of games the user is queued
                for.
            notifications (List[GameId]): List of ids of games the user has
                notifications for.
            notification_id (Optional[MessageId]): Id of the notification message
                sent to the user.
        """

        active_games: List[GameId]
        queued_games: List[GameId]
        notifications: List[GameId]
        notification_id: Optional[MessageId] = None

    @staticmethod
    async def join_game(
        user_id: UserId,
        game_id: GameId,
    ) -> bool:
        """Adds a game to a user's active_games or queued_games.

        Adds a game to a user's active_games if the user has not reached the
        max number of active games, else adds the game to the user's
        queued_games if the user has not reached the max number of queued games.

        Args:
            user_id (UserId): Id of user to add the game to.
            game_id (GameId): Id of game to add to user.

        Returns:
            bool: True if the user can not join game, else False.
        """

        if await UserStatus.__pool.exists(str(user_id)):
            return await UserStatus.__join_game_existing_user(user_id, game_id)

        await UserStatus.__join_game_new_user(user_id, game_id)
        return True

    @staticmethod
    @pipeline_watch(__pool, "user_id")
    async def __join_game_existing_user(
        pipe: redis_async_client.Pipeline,
        user_id: UserId,
        game_id: GameId,
    ) -> bool:
        """Adds a game to a user's active_games or queued_games.

        Should only be called by join_game when a user already
        existst in the db.

        Will return false if user is maxed out on games.
        """

        user_status = await pipe.json().get(user_id)
        user_status = UserStatus.User(**user_status)

        if (
            game_id not in user_status.active_games
            and game_id not in user_status.queued_games
        ):
            pipe.multi()
            if len(user_status.active_games) >= UserStatus.__max_active_games:
                if len(user_status.queued_games) >= UserStatus.__max_queued_games:
                    return False
                pipe.json().arrappend(str(user_id), ".queued_games", game_id)
            else:
                pipe.json().arrappend(str(user_id), ".active_games", game_id)
            await pipe.execute()

        return True

    @staticmethod
    async def __join_game_new_user(
        user_id: UserId,
        game_id: GameId,
    ) -> None:
        """Creates a new user in the db with provided game id as an active game.

        Should only be called by join_game.
        """

        await UserStatus.__pool.json().set(
            user_id,
            ".",
            asdict(
                UserStatus.User(
                    active_games=[game_id], queued_games=[], notifications=[]
                )
            ),
        )

    @staticmethod
    async def get(user_id: UserId) -> Optional[User]:
        """Gets the status of a user.

        Args:
            user_id (UserId): Id of user to get status of.

        Returns:
            Optional[User]: Returns user status if user is in db, else None.
        """

        if user_status := await UserStatus.__pool.json().get(user_id):
            return UserStatus.User(**user_status)

    @staticmethod
    async def check_users_are_ready(user_ids: List[UserId], game_id: GameId) -> bool:
        """Checks if game is ready to start.

        Checks if a game id is in all users active games if so the game is not
        queued and could be started.

        Args:
            user_ids (List[UserId]): List of user ids to check.
            game_id (GameId): Id of game to check for in users active games.

        Raises:
            UserNotFound: Raised if a user to check is not in the db.

        Returns:
            bool: Returns True if all users have game in active games, else False.
        """

        for user_id in user_ids:
            user_status = await UserStatus.get(user_id)
            if user_status:
                if game_id not in user_status.active_games:
                    return False
            else:
                raise UserNotFound(user_id)
        return True

    @staticmethod
    async def add_notifiction(user_id: UserId, game_id: GameId) -> None:
        """Adds a game to a user's notifications.

        Args:
            user_id (UserId): Id of user to add notification to.
            game_id (GameId): Id of game to add to user's notifications.

        Raises:
            UserNotFound: Raised if user_id is not found in db.
        """

        if not (user_status := await UserStatus.get(user_id)):
            raise UserNotFound(user_id)

        # Makes sure there are no duplicates
        if game_id not in user_status.notifications:
            UserStatus.__pool.json().arrappend(str(user_id), ".notifications", game_id)

    @staticmethod
    async def remove_notification(user_id: UserId, game_id: GameId) -> bool:
        """Removes a game from a user's notifications.

        Args:
            user_id (UserId): Id of user to remove notification from.
            game_id (GameId): Id of game to remove from user's notifications.

        Raises:
            UserNotFound: Raised if user_id is not found in db.

        Returns:
            bool: True if the notification was found, else False.
        """

        if not (user_status := await UserStatus.get(user_id)):
            raise UserNotFound(user_id)

        removed = False

        if game_id in user_status.notifications:
            UserStatus.__pool.json().arrpop(
                str(user_id),
                ".notifications",
                user_status.notifications.index(game_id),
            )

            removed = True

        return removed

    @staticmethod
    async def set_notification_id(user_id: UserId, message_id: MessageId) -> None:
        """Sets the notification id of a user.

        Args:
            user_id (UserId): Id of user to set notification id for.
            message_id (MessageId): Id of discord message to set as
                notification id.

        Raises:
            UserNotFound: Raised if user_id is not found in db.
        """

        try:
            await UserStatus.__pool.json().set(user_id, ".notification_id", message_id)
        except redis.ResponseError:
            raise UserNotFound(user_id)

    @staticmethod
    async def remove_notification_id(user_id: UserId) -> None:
        """Removes the notification id of a user.

        Args:
            user_id (UserId): User to remove notification id from.

        Raises:
            UserNotFound: Raised if user_id is not found in db.
        """

        try:
            await UserStatus.__pool.json().set(user_id, ".notification_id", None)
        except redis.ResponseError:
            raise UserNotFound(user_id)

    @staticmethod
    async def clear_game(
        user_ids: List[UserId],
        game_id: GameId,
    ) -> tuple[Set[GameId], List[UserId]]:
        """Removes a game from users active games and queued games.

        Given a list of users and a game id, removes the game from all users
        no mattter its state. Checks if queued games can be moved to active and
        if there is a left over notifications that can be remove.

        Args:
            user_ids (List[UserId]): List of user ids to remove game from.
            game_id (GameId): Id of game to remove from users.

        Returns:
            tuple[List[GameId], List[UserId]]: Tuple containing a list of game ids
                that were moved from queued_games to active_games and a list of
                users who had a notification removed. in form (moved up games,
                notifications removed from).
        """

        moved_up_games: Set[GameId] = set()
        notifications_removed_from: List[UserId] = []

        for user in user_ids:
            try:
                (
                    user_moved_up_games,
                    notification_removed,
                ) = await UserStatus.__remove_game(game_id, user)

                if moved_up_ids := user_moved_up_games:
                    for move_up_id in moved_up_ids:
                        moved_up_games.add(move_up_id)

                if notification_removed:
                    notifications_removed_from.append(user)

            except GameNotFound:
                print(f"User {user} was not in game {game_id}")
            except UserNotFound:
                print(f"User {user} was not found")

        return (moved_up_games, notifications_removed_from)

    @staticmethod
    @pipeline_watch(__pool, "user_id")
    async def __remove_game(
        pipe: redis_async_client.Pipeline,
        game_id: GameId,
        user_id: UserId,
    ) -> tuple[Optional[List[GameId]], bool]:
        """Removes a game from a user's active_games or queued_games"""

        # Flags for if the user is deleted and if a notification was removed
        deleted = False
        removed_notification = False

        if not (user_status := await UserStatus.get(user_id)):
            raise UserNotFound(user_id)

        if (
            game_id not in user_status.active_games
            and game_id not in user_status.queued_games
        ):
            raise GameNotFound(f"{game_id} not found in user {user_id}'s games")

        # Gets the type of game the game is in and its index
        game_type, game_index = (
            ("active_games", user_status.active_games.index(game_id))
            if game_id in user_status.active_games
            else ("queued_games", user_status.queued_games.index(game_id))
        )

        pipe.multi()

        # Removes game from active_games or queued_games
        pipe.json().arrpop(str(user_id), f".{game_type}", game_index)

        # Removes game from notifications if it is there
        if game_id in user_status.notifications:
            pipe.json().arrpop(
                str(user_id), ".notifications", user_status.notifications.index(game_id)
            )
            removed_notification = True

        # Checks if user can be deleted
        if (
            # Its == 1 because this uses outdated data from before we delete one
            len(user_status.active_games) + len(user_status.queued_games)
            == 1
        ):
            pipe.json().delete(user_id)
            deleted = True

        await pipe.execute()

        # Moves up games if there is space
        moved_up_games: Optional[List[GameId]] = None
        if not deleted:
            moved_up_games = await UserStatus.__move_up_games(user_id)

        return (moved_up_games, removed_notification)

    @staticmethod
    @pipeline_watch(__pool, "user_id", UserNotFound)
    async def __move_up_games(
        pipe: redis_async_client.Pipeline, user_id: UserId
    ) -> List[GameId]:
        """Moves games from queued_games to active_games if there is space"""

        flag = True
        moved_games = []

        if not (user_status := await UserStatus.get(user_id)):
            raise UserNotFound(user_id)

        while flag:
            # Checks if there is space in active_games and if there are games in queued_games
            if (
                len(user_status.active_games) < UserStatus.__max_active_games
                and len(user_status.queued_games) > 0
            ):
                pipe.multi()
                pipe.json().arrpop(str(user_id), ".queued_games", 0)
                pipe.json().arrappend(
                    str(user_id), ".active_games", user_status.queued_games[0]
                )
                moved_games.append((await pipe.execute())[0])

                # Updates local object for next iteration
                user_status.active_games.append(user_status.queued_games.pop(0))
            else:
                flag = False

        return moved_games
