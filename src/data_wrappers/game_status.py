"""Contains the GameStatus class which is used keep track of games"""

import asyncio
import random
import string
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple

import redis
import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client

from data_types import GameId, UserId
from exceptions import GameNotFound, UserNotFound

from .utils import RedisDb, is_main_instance, pipeline_watch


class GameStatus:
    """API wrapper for db which handles the status of games.

    All data in the db is in the key:value form:
        GameId: Game
    """

    # All games have a shadow key with an expiry time. This allows for the game
    # status to be retrevied after the game expires cause only the shadow key will
    # be removed for the db at the expiry time.

    # Redis db number and redis connection pool
    __db_number = 1
    __pool = redis_sync.Redis(db=__db_number)

    @dataclass
    class Game:
        """Dataclass for storing game status.

        Attributes:
            state (Literal[0, 1, 2]): State of game.
                0: Pending
                1: Queued
                2: In Progress
            game_module_name (str): Name of game module being played.
            starting_user (UserId): Id of user who started the game.
            usernames (Dict[str, str]): Dictionary of user ids and usernames.
                In the form of {user_id: username}.
            all_users (List[UserId]): List of ids of all users invited to play
                game.
            pending_users (List[UserId]): List of users who have not accepted
                game invite.
        """

        state: Literal[0, 1, 2]
        game_module_name: str
        starting_user: UserId
        all_users: List[UserId]
        pending_users: List[UserId]
        usernames: Dict[str, str]

        def get_accepted_users(self) -> List[UserId]:
            """Gets list of users who have accepted invite to play the game.

            Returns:
                List[UserId]: List of user ids of users who have accepted invite
                    to play the game.
            """

            return [
                user_id
                for user_id in self.pending_users
                if user_id not in self.pending_users
            ]

        @staticmethod
        def generate_fake(
            state: Literal[0, 1, 2],
            game_module_name: str,
            user_count: int,
            pending_user_count: int,
            users_to_include: Optional[List[Tuple[UserId, str]]] = None,
        ):
            """Creates fake game status.

            User ids are the values from 0 to user_count - 1 with the usernames
                being "User 0" to "User {user_count - 1}".

            Starting user is 0.

            The pending users are the values from user_count - 1
                to user_count - pending_user_count - 1.

            If users_to_include is not None, listed ids will be put in non-pending users.
            If user from users_to_include is put in pending then it will be users at
                the start of the list.
            """

            all_users = []
            pending_users = []
            usernames = {}
            for i in range(user_count, 0, -1):
                # Adds users from users_to_include first
                if users_to_include and len(users_to_include):
                    user_id, username = users_to_include.pop()
                    usernames[user_id] = username
                    all_users.append(user_id)
                else:
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

    # Functions to be called when a game expires. The key is the name of the
    # function and the value is the function itself which should accept the
    # game id of the expiring game as a parameter.
    __expire_callbacks: dict[str, Callable[[GameId], Awaitable[None]]] = {}

    @staticmethod
    def __get_shadow_key(game_id: GameId) -> str:
        """Returns the shadow key version of a game_id"""

        return f"shadowKey:{game_id}"

    @staticmethod
    def __create_game_id() -> GameId:
        """Returns a random game id"""

        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    @staticmethod
    async def add(game_status: Game, expire_time: timedelta) -> GameId:
        """Adds game status to db.

        This creates and returns the game id that should be used to identify the
        game throughout the rest of the program.

        Args:
            game_status (Game): Game status to add to db.
            expire_time (timedelta): Time before game expires.

        Returns:
            GameId: Id of game added to db.
        """

        new_game_id = GameStatus.__create_game_id()

        await GameStatus.__pool.json().set(new_game_id, ".", asdict(game_status))

        # Creates shadow key that expires so that the game
        # can be retrevied after it expires
        shadow_key = GameStatus.__get_shadow_key(new_game_id)
        await GameStatus.__pool.set(shadow_key, -1)
        await GameStatus.__pool.expire(shadow_key, expire_time)

        return new_game_id

    @staticmethod
    async def get(game_id: GameId) -> Game:
        """Gets game status from db.

        Args:
            game_id (GameId): Id of game to get status for.

        Raises:
            GameNotFound: Raised if game_id is not found in db.

        Returns:
            Game: Status of the game.
        """

        if game_state := await GameStatus.__pool.json().get(game_id):
            return GameStatus.Game(**game_state)
        raise GameNotFound(game_id)

    @staticmethod
    async def set_expiry(game_id: GameId, extend_time: Optional[timedelta]):
        """Sets an amount of time before a game expires.

        Args:
            game_id (GameId): Id of game the change the expiry time for.
            extend_time (timedelta, optional): Time to set expiry timer to.
                If None then the game will be set to never expire.

        Raises:
            GameNotFound: Raised if game_id is not found in db.
        """

        if await GameStatus.__pool.exists(game_id):
            shadow_key = GameStatus.__get_shadow_key(game_id)
            if extend_time:
                # Only need to update shadow key cause it is the only one that expires
                await GameStatus.__pool.expire(shadow_key, extend_time)
            else:
                await GameStatus.__pool.persist(shadow_key)
        else:
            raise GameNotFound(game_id)

    @staticmethod
    async def set_game_state(game_id: GameId, state: Literal[0, 1, 2]) -> None:
        """Sets the state of a game.

        Args:
            game_id (GameId): Id of game to change state of.
            state (Literal[0, 1, 2]): State to change game to. Should be one of
                the following:
                    0: Pending
                    1: Queued
                    2: In Progress

        Raises:
            GameNotFound: Raised if game_id is not found in db.
        """

        try:
            await GameStatus.__pool.json().set(game_id, ".state", state)
        except redis.ResponseError:
            raise GameNotFound(game_id)

    @staticmethod
    @pipeline_watch(__pool, "game_id", GameNotFound)
    async def user_accepted(
        pipe: redis_async_client.Pipeline,
        game_id: GameId,
        user_id: int,
    ) -> List[int]:
        """Removes user from pending users.

        Should be used to remove users who have accepted the game invite from.

        Args:
            game_id (GameId): Id of game to remove pending users from.
            user_id (int): Id of user to remove from pending users.

        Raises:
            UserNotFound: Raised if user_id is not found in pending users list.
            GameNotFound: Raised if game_id is not found in db.

        Returns:
            List[int]: List of remaining pending users after removing passed
                users id.
        """

        game_status = await GameStatus.get(game_id)

        if user_id in game_status.pending_users:
            pipe.multi()

            pipe.json().arrpop(
                game_id,
                ".pending_users",
                game_status.pending_users.index(user_id),
            )
            pipe.json().get(game_id, ".pending_users")

            results = await pipe.execute()

            return results[1]

        else:
            raise UserNotFound(user_id)

    @staticmethod
    async def delete(game_id: GameId) -> None:
        """Deletes game status from db.

        Does not do anything if game_id is not found in db.

        Args:
            game_id (GameId): Id of game to delete status for.
        """

        await GameStatus.__pool.delete(game_id)

        # Deletes shadow key cause their expire event could be listened to
        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.delete(shadow_key)

    @staticmethod
    def handle_game_expire(
        fn: Callable[[GameId], Awaitable[None]]
    ) -> Callable[[GameId], Awaitable[None]]:
        """Decorator for adding a callback to be called when a game expires.

        Does not effect the decorated function in any way.

        If the callback of same name is already added then the function will
        not be added.

        Game will not be automatically deleted from db. This should be done
        manually in a callback function.

        Args:
            fn (Callable[[GameId], Awaitable[None]]): Function to be called when
                game expires. Should accept game id as a parameter.
        """

        if (name := fn.__name__) not in GameStatus.__expire_callbacks:
            GameStatus.__expire_callbacks[name] = fn

        return fn

    @staticmethod
    @RedisDb.is_pubsub_callback(f"__keyevent@{__db_number}__:expired")
    async def __expire_handler(msg: Any):
        """Handler for when a key expires in game status db"""

        try:
            msg = msg["data"].decode("utf-8")
        except AttributeError:
            raise ValueError("Message not in utf-8 format")
        else:
            # Checks if message is a shadow key
            if msg.startswith(GameStatus.__get_shadow_key("")):
                game_id = msg.split(":")[1]

                for callback in GameStatus.__expire_callbacks.values():
                    # Uses ensure_future instead of await to avoid blocking
                    asyncio.ensure_future(callback(game_id))
            else:
                print("Not shadow key")

    @staticmethod
    @is_main_instance
    async def remove_expire_handler(
        game_expire_callback: Callable[[GameId, Game], Awaitable[None]]
    ):
        """Removes a registered callback that is called when a game expires.

        The function passed to this function should be a function that was
        previously registed to this class using the handle_game_expire decorator.

        Args:
            game_expire_callback (Callable[[GameId, Game], Awaitable[None]]):
                Function to be removed.

        Raises:
            KeyError: If callback is not found.
        """

        if (name := game_expire_callback.__name__) not in GameStatus.__expire_callbacks:
            raise KeyError("Callback with that name not found")

        else:
            del GameStatus.__expire_callbacks[name]
