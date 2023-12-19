import asyncio
import random
import string
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Awaitable, Callable, Dict, List, Literal, Mapping, Optional

import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client

from data_types import GameId, UserId
from exceptions import GameNotFound, PlayerNotFound

from .utils import RedisDb, is_main_instance, pipeline_watch


class GameStatus(RedisDb):
    """
    API wrapper for reddis db which handles the status of games
    all entrys have a shadow key to keep track of when games expire.
    This allows for the game status to be retrevied after the game has expired.

    IMPORTANT: For the games to expire properly the start_expire_listener function
    must be called before any games are added to the db

    All data in the db is in form
    GameId: GameState
    """

    __db_number = 1
    __pool = redis_sync.Redis(db=__db_number)

    @dataclass
    class Game:
        """
        Dataclass for game state

        Used to store data on all games no matter the game type

        status[int]:
            0 = unconfirmed | 1 = confirmed but queued | 2 = in progress

        game[str]:
            Name of game type

        starting_player[int]:
            Player id of player who started the game

        player_names[Mapping[str, str]]:
            Mapping of player id to player name

        confirmed_players[List[int]]:
            List of player ids who have agreed to play the game

        unconfirmed_players[List[int]]:
            List of player ids who have not yet agreed to play the game
        """

        status: Literal[0, 1, 2]
        game: str
        starting_player: int
        player_names: Dict[str, str]
        all_players: List[UserId]
        unconfirmed_players: List[UserId]

        def confirmed_players(self) -> List[UserId]:
            """
            Returns a list of all confirmed players
            """

            return list(
                filter(
                    lambda player_id: player_id not in self.unconfirmed_players,
                    self.all_players,
                )
            )

    # Callbacks for when games expire
    __expire_callbacks: dict[str, Callable[[GameId], Awaitable[None]]] = {}

    @staticmethod
    def __get_shadow_key(game_id: GameId) -> str:
        """
        Returns the shadow key version of a game_id
        """

        return f"shadowKey:{game_id}"

    @staticmethod
    def __create_game_id() -> GameId:
        """
        Generates a random game id and returns it
        """

        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    @staticmethod
    async def add(game_status: Game, expire_time: timedelta) -> GameId:
        """
        Adds a game to the db

        Returns the game id
        """

        game_id = GameStatus.__create_game_id()

        await GameStatus.__pool.json().set(game_id, ".", asdict(game_status))

        # Creates shadow key that expires so that the game
        # can be retrevied after it expires
        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.set(shadow_key, -1)
        await GameStatus.__pool.expire(shadow_key, expire_time)

        return game_id

    @staticmethod
    async def get(game_id: GameId) -> Game:
        """
        Returns game data if game is found

        Raises ActiveGameNotFound if game is not found
        """

        if game_state := await GameStatus.__pool.json().get(game_id):
            return GameStatus.Game(**game_state)
        raise GameNotFound(game_id)

    @staticmethod
    async def set_expiry(game_id: GameId, extend_time: Optional[timedelta]):
        """
        Sets the amount of time before a game expires
        """

        shadow_key = GameStatus.__get_shadow_key(game_id)
        if extend_time:
            # Only need to update shadow key cause it is the only one that expires
            await GameStatus.__pool.expire(shadow_key, extend_time)
        else:
            await GameStatus.__pool.persist(shadow_key)

    @staticmethod
    async def set_game_unconfirmed(game_id: GameId):
        await GameStatus.__pool.json().set(game_id, ".status", 0)

    @staticmethod
    async def set_game_queued(game_id: GameId):
        await GameStatus.__pool.json().set(game_id, ".status", 1)

    @staticmethod
    async def set_game_in_progress(game_id: GameId):
        await GameStatus.__pool.json().set(game_id, ".status", 2)

    @staticmethod
    @pipeline_watch(__pool, "game_id", GameNotFound)
    async def confirm_player(
        pipe: redis_async_client.Pipeline,
        game_id: GameId,
        player_id: int,
    ) -> List[int]:
        """
        Adds a player to the confirmed list and removes them from the
        unconfirmed list

        Raises ActiveGameNotFound if game is not found
        Raises PlayerNotFound if player is not in unconfirmed list

        Returns updated unconfirmed_players list
        """

        game_status = await GameStatus.get(game_id)

        if player_id in game_status.unconfirmed_players:
            # Switch to buffered modweeke to make sure all commands
            # are executed without any external changes to the lists
            pipe.multi()
            # Moves player from unconfirmed to confirmed list
            pipe.json().arrpop(
                game_id,
                ".unconfirmed_players",
                game_status.unconfirmed_players.index(player_id),
            )
            pipe.json().get(game_id, ".unconfirmed_players")
            results = await pipe.execute()

            return results[1]

        else:
            raise PlayerNotFound(player_id)

    @staticmethod
    async def delete(game_id: GameId):
        """
        Deletes game status from db
        """

        await GameStatus.__pool.delete(game_id)

        # Deletes shadow key cause their expire event could be listened to
        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.delete(shadow_key)

    @staticmethod
    def handle_game_expire(
        fn: Callable[[GameId], Awaitable[None]]
    ) -> Callable[[GameId], Awaitable[None]]:
        if (name := fn.__name__) not in GameStatus.__expire_callbacks:
            GameStatus.__expire_callbacks[name] = fn

        return fn

    @staticmethod
    @RedisDb.is_pubsub_callback(f"__keyevent@{__db_number}__:expired")
    async def __expire_handler(msg: Any):
        """
        Handler for when a key expires

        Runs all the callbacks registed with the add_expire_handler function.

        Raises Exception if message is not in utf-8 format
        Raises Exception if unknown error occurs
        Raises ActiveGameNotFound if the expired game is not found
        """

        try:
            msg = msg["data"].decode("utf-8")
        except AttributeError:
            raise ValueError("Message not in utf-8 format")
        else:
            # Checks if message is a shadow key
            if msg.startswith(GameStatus.__get_shadow_key("")):
                game_id = msg.split(":")[1]

                expired_game_data = await GameStatus.get(game_id)

                for callback in GameStatus.__expire_callbacks.values():
                    await callback(game_id)
            else:
                print("Not shadow key")

    @staticmethod
    @is_main_instance
    async def remove_expire_handler(
        game_expire_callback: Callable[[GameId, Game], Awaitable[None]]
    ):
        """
        Removes a callback from the list of callbacks to be called when a key expires
        """

        if (name := game_expire_callback.__name__) not in GameStatus.__expire_callbacks:
            raise KeyError("Callback with that name not found")

        else:
            del GameStatus.__expire_callbacks[name]
