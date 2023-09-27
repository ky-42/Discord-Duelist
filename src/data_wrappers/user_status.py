from dataclasses import asdict, dataclass
from typing import List, Optional

import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client

from data_types import GameId, MessageId, UserId
from exceptions.game_exceptions import ActiveGameNotFound
from exceptions.general_exceptions import PlayerNotFound

from .utils import pipeline_watch


class UserStatus:

    """
    API wrapper for reddis db which handles the status of players

    All data in the db is in the form
    UserId: UserState
    """

    __db_number = 2
    __pool = redis_sync.Redis(db=__db_number)

    # Max number of games a user can be in at once
    __max_games = 6

    @dataclass
    class UserState:
        current_games: List[GameId]
        queued_games: List[GameId]
        notifications: List[GameId]
        notification_id: Optional[MessageId] = None

    @staticmethod
    async def get_status(user_id: UserId) -> Optional[UserState]:
        """
        Returns the UserState of a user if they exist, otherwise returns None
        """

        if current_status := await UserStatus.__pool.json().get(user_id):
            return UserStatus.UserState(**current_status)

    @staticmethod
    async def check_in_games(
        user_id: UserId,
        number_of_games: int = __max_games,
    ) -> bool:
        """
        Checks if a user is in at least the number of games specified

        Returns True if they are, otherwise returns False
        """

        current_status = await UserStatus.get_status(user_id)

        if current_status:
            return len(current_status.current_games) >= number_of_games
        return False

    @staticmethod
    async def join_game(
        user_id: UserId,
        game_id: GameId,
    ):
        """
        The only way users should be added to a game
        """

        # Checks if user already exists in db and
        # calls the appropriate function
        if await UserStatus.__pool.exists(str(user_id)):
            await UserStatus.__join_game_existing_user(user_id, game_id)
        else:
            await UserStatus.__join_game_new_user(user_id, game_id)

    @staticmethod
    @pipeline_watch(__pool, "user_id")
    async def __join_game_existing_user(
        pipe: redis_async_client.Pipeline,
        user_id: UserId,
        game_id: GameId,
    ):
        """
        Adds a game to a user's current_games or queued_games

        Should only be called by join_game when a user already
        existst in the db
        """

        current_status = await pipe.json().get(user_id)
        current_status = UserStatus.UserState(**current_status)

        if (
            game_id not in current_status.current_games
            and game_id not in current_status.queued_games
        ):
            # If user is not in the game, add game to current_games or queued_games
            # depending on how many games the user is already in
            pipe.multi()
            if len(current_status.current_games) >= UserStatus.__max_games:
                pipe.json().arrappend(str(user_id), ".queued_games", game_id)
            else:
                pipe.json().arrappend(str(user_id), ".current_games", game_id)
            await pipe.execute()
        else:
            print(f"User {user_id} is already in game {game_id}")

    @staticmethod
    async def __join_game_new_user(
        user_id: UserId,
        game_id: GameId,
    ):
        """
        Creates a new user in the db with the provided game_id
        as their current_game

        Should only be called by join_game
        """
        await UserStatus.__pool.json().set(
            user_id,
            ".",
            asdict(
                UserStatus.UserState(
                    current_games=[game_id], queued_games=[], notifications=[]
                )
            ),
        )

    @staticmethod
    async def check_users_are_ready(game_id: GameId, user_ids: List[UserId]) -> bool:
        """
        Checks if all users are ready to start a game

        A game is ready if all users have the provided game_id in their current_games
        """

        for user_id in user_ids:
            user_status = await UserStatus.get_status(user_id)
            if user_status:
                if game_id not in user_status.current_games:
                    return False
        return True

    @staticmethod
    async def clear_game(
        game_id: GameId,
        user_ids: List[UserId],
    ) -> List[GameId]:
        """
        Removes a game from all users' current_games and queued_games

        Returns a list of game_ids that were moved from queued_games to current_games
        """

        move_up_games: List[GameId] = []

        for user in user_ids:
            try:
                # Removes the game and stores the ids of the games that moved from queued_games to current_games
                if move_up_ids := await UserStatus.__remove_game(game_id, user):
                    for move_up_id in move_up_ids:
                        if move_up_id not in move_up_games:
                            move_up_games.append(move_up_id)

            except ActiveGameNotFound:
                print(f"User {user} was not in game {game_id}")
            except PlayerNotFound:
                print(f"User {user} was not found")

        return move_up_games

    @staticmethod
    @pipeline_watch(__pool, "user_id")
    async def __remove_game(
        pipe: redis_async_client.Pipeline,
        game_id: GameId,
        user_id: UserId,
    ) -> Optional[List[GameId]]:
        """
        Removes a game from a user's current_games or queued_games

        If the user is not in the game, raises ActiveGameNotFound
        If the user is not found in the db, raises PlayerNotFound

        Returns the id of the queued game that was moved to current_games
        if that happended
        """

        # Makes sure user exists and gets their current status
        if current_status := await UserStatus.get_status(user_id):
            # If game is in current games or queued games and remove it
            if (
                game_id not in current_status.current_games
                and game_id not in current_status.queued_games
            ):
                raise ActiveGameNotFound(game_id)

            game_type = (
                "current_games"
                if game_id in current_status.current_games
                else "queued_games"
            )

            if game_type == "current_games":
                game_index = current_status.current_games.index(game_id)
            else:
                game_index = current_status.queued_games.index(game_id)

            deleted = False

            pipe.multi()
            pipe.json().arrpop(str(user_id), f".{game_type}", game_index)
            if (
                # Its == 1 because this uses outdated data from before we delete one
                len(current_status.current_games) + len(current_status.queued_games)
                == 1
            ):
                # If the user is not in any games, delete them from the db
                deleted = True
                pipe.json().delete(user_id)
            await pipe.execute()

            if not deleted:
                # If the user is still in the db, move up a game from queued_games to current_games
                return await UserStatus.move_up_games(user_id)

        else:
            raise PlayerNotFound(user_id)

    @staticmethod
    @pipeline_watch(__pool, "user_id")
    async def move_up_games(
        pipe: redis_async_client.Pipeline, user_id: UserId
    ) -> List[GameId]:
        # Moves games from queued_games to current_games if there is room
        # TODO maybe make this use pubsub so that its not on the calling function
        # to check if the moved up game is ready cause GameAdmin could just link to this
        moved_games = []

        flag = True
        while flag:
            if current_status := await UserStatus.get_status(user_id):
                if (
                    len(current_status.current_games) < UserStatus.__max_games
                    and len(current_status.queued_games) > 0
                ):
                    pipe.multi()
                    pipe.json().arrpop(str(user_id), ".queued_games")
                    pipe.json().arrappend(
                        str(user_id), ".current_games", current_status.queued_games[-1]
                    )
                    moved_games.append((await pipe.execute())[0])
                else:
                    flag = False
            else:
                raise PlayerNotFound(user_id)

        return moved_games

    @staticmethod
    @pipeline_watch(__pool, "user_id")
    async def add_notifiction(
        pipe: redis_async_client.Pipeline, game_id: GameId, user_id: UserId
    ):
        """
        Adds a game to a user's notifications
        """

        if user_status := await UserStatus.get_status(user_id):
            # Makes sure there are no duplicates
            if game_id not in user_status.notifications:
                pipe.multi()
                pipe.json().arrappend(
                    str(user_id),
                    ".notifications",
                )
                await pipe.execute()
        else:
            raise PlayerNotFound(user_id)

    @staticmethod
    async def amount_of_notifications(user_id: UserId) -> int:
        """
        Returns the amount of notifications a user has
        """

        if current_status := await UserStatus.get_status(user_id):
            return len(current_status.notifications)
        return 0

    @staticmethod
    @pipeline_watch(__pool, "user_id")
    async def remove_notification(
        pipe: redis_async_client.Pipeline, game_id: GameId, user_id: UserId
    ):
        """
        Removes a game from a user's notifications
        """
        if user_status := await UserStatus.get_status(user_id):
            if game_id in user_status.notifications:
                pipe.multi()
                pipe.json().arrpop(
                    str(user_id),
                    ".notifications",
                    user_status.notifications.index(game_id),
                )
                await pipe.execute()
        else:
            raise PlayerNotFound(user_id)

    @staticmethod
    async def set_notification_id(user_id: UserId, message_id: MessageId) -> None:
        """
        Sets the notification id of a user
        """

        await UserStatus.__pool.json().set(user_id, ".notification_id", message_id)

    @staticmethod
    async def get_notification_id(user_id: UserId) -> Optional[MessageId]:
        """
        Gets the notification id of a user
        """

        if notification_id := await UserStatus.__pool.json().get(
            user_id, ".notification_id"
        ):
            return notification_id

    @staticmethod
    async def remove_notification_id(user_id: UserId) -> None:
        """
        Removes the notification id of a user
        """

        await UserStatus.__pool.json().delete(user_id, ".notification_id")
