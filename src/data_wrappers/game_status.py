import asyncio
import random
import string
from ast import Await
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Awaitable, Callable, List, Mapping

import redis.asyncio as redis_sync
import redis.asyncio.client as redis_async_client

from data_types import GameId
from exceptions.game_exceptions import ActiveGameNotFound
from exceptions.general_exceptions import FuncExists, FuncNotFound, PlayerNotFound

from .utils import pipeline_watch


class GameStatus:
    """
    API wrapper for reddis db which handles the status of games
    all entrys have a shadow key to keep track of when games expire.
    This allows for the game status to be retrevied after the game has expired

    All data in the db is in form
    GameId: GameState
    """

    __db_number = 1
    __pool = redis_sync.Redis(db=__db_number)

    @dataclass
    class GameState:
        """
        Dataclass for game state

        Used to store data on all games no matter the game type

        status[int]:
            0 = unconfirmed | 1 = confirmed but queued | 2 = in progress

        game[str]:
            Name of game type

        bet[int]:
            Amount of points bet on game

        starting_player[int]:
            Player id of player who started the game

        player_names[Mapping[str, str]]:
            Mapping of player id to player name

        confirmed_players[List[int]]:
            List of player ids who have agreed to play the game

        unconfirmed_players[List[int]]:
            List of player ids who have not yet agreed to play the game
        """

        status: int
        game: str
        bet: int
        starting_player: int
        player_names: Mapping[str, str]
        confirmed_players: List[int]
        unconfirmed_players: List[int]

    # Callbacks for when games expire
    __expire_callbacks: dict[str, Callable[[GameId, GameState], Awaitable[None]]] = {}
    # Instance of pubsub task. Used to handle shadow key expire events
    __pubsub_task: asyncio.Task | None = None

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
    async def add_game(game_status: GameState, expire_time: timedelta) -> GameId:
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
    async def get_game(game_id: GameId) -> GameState:
        """
        Returns game data if game is found

        Raises ActiveGameNotFound if game is not found
        """

        if game_state := await GameStatus.__pool.json().get(game_id):
            return GameStatus.GameState(**game_state)
        raise ActiveGameNotFound

    @staticmethod
    async def set_game_expire(game_id: GameId, extend_time: timedelta):
        """
        Sets the amount of time before a game expires
        """

        # Only need to update shadow key cause it is the only one that expires
        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.expire(shadow_key, extend_time)

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
    @pipeline_watch(__pool, "game_id", ActiveGameNotFound)
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

        # Make sure player is in the unconfirmed list
        if (
            unconfirmed_player_index := await pipe.json().arrindex(
                game_id, ".unconfirmed_players", player_id
            )
        ) > -1:
            # Switch to buffered mode to make sure all commands
            # are executed without any external changes to the lists
            pipe.multi()
            # Moves player from unconfirmed to confirmed list
            pipe.json().arrpop(
                game_id, ".unconfirmed_players", unconfirmed_player_index
            )
            pipe.json().arrappend(game_id, ".confirmed_players", player_id)
            pipe.json().get(game_id, ".unconfirmed_players")
            results = await pipe.execute()

            return results[2]

        else:
            raise PlayerNotFound(player_id)

    @staticmethod
    async def delete_game(game_id: GameId):
        """
        Deletes game status from db
        """

        await GameStatus.__pool.delete(game_id)

        # Deletes shadow key cause their expire event could be listened to
        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.delete(shadow_key)

    @staticmethod
    async def add_expire_handler(
        game_expire_callback: Callable[[GameId, GameState], Awaitable[None]]
    ):
        """
        Adds a callback to be called when a game expires

        game_expire_callback[Callable[[GameId, GameState], Awaitable[None]]]:
            The passed function must accept the GameId of the expired game
            as its first parameter and the GameState of the expired game as
            its second parameter. It must also be asyncronous and return nothing

        Raises FuncExists if a function with the same name has already been added

        IMPORTANT: Could cause problems if multiple instances of the bot are running
        """

        if not GameStatus.__pubsub_task:
            # Sets config to listen for expire events
            await GameStatus.__pool.config_set("notify-keyspace-events", "Ex")

            # Creates pubsub object and subscribes to expire events
            pubsub_obj = GameStatus.__pool.pubsub()
            await pubsub_obj.psubscribe(
                **{
                    f"__keyevent@{GameStatus.__db_number}__:expired": GameStatus.expire_handler
                }
            )

            # Starts pubsub object and stores task
            GameStatus.__pubsub_task = asyncio.create_task(pubsub_obj.run())

        if (name := game_expire_callback.__name__) not in GameStatus.__expire_callbacks:
            # Stores callback by name
            GameStatus.__expire_callbacks[name] = game_expire_callback

        else:
            raise FuncExists(name)

    @staticmethod
    async def expire_handler(msg):
        """
        Handler for when a key expires

        Runs all the callbacks registed with the add_expire_handler function.

        Raises Exception if message is not in utf-8 format
        Raises Exception if unknown error occurs
        Raises ActiveGameNotFound if the expired game is not found

        IMPORTANT: Could cause problems if multiple instances of the bot are running
        """

        try:
            msg = msg["data"].decode("utf-8")
        except AttributeError:
            raise Exception("Message not in utf-8 format")
        except:
            raise Exception("Unknown error")
        else:
            # Checks if message is a shadow key
            if msg.startswith(GameStatus.__get_shadow_key("")):
                game_id = msg.split(":")[1]

                expired_game_data = await GameStatus.get_game(game_id)
                await GameStatus.delete_game(game_id)

                for callback in GameStatus.__expire_callbacks.values():
                    await callback(game_id, expired_game_data)
            else:
                print("Not shadow key")

    @staticmethod
    async def remove_expire_handler(
        game_expire_callback: Callable[[GameId, GameState], Awaitable[None]]
    ):
        """
        Removes a callback from the list of callbacks to be called when a key expires

        Raises FuncNotFound if function is not found

        IMPORTANT: Could cause problems if multiple instances of the server are running
        """

        if (name := game_expire_callback.__name__) not in GameStatus.__expire_callbacks:
            raise FuncNotFound(name)

        else:
            del GameStatus.__expire_callbacks[name]

            # If no callbacks left stops pubsub task and resets config for performance
            if (
                len(GameStatus.__expire_callbacks.keys()) == 0
                and GameStatus.__pubsub_task
            ):
                await GameStatus.__pool.config_set("notify-keyspace-events", "")
                GameStatus.__pubsub_task.cancel()
                # FIGURE OUT WHY THIS IS NEEDED IF AT ALL
                # I put it here cause it was in the example
                await GameStatus.__pubsub_task

                GameStatus.__pubsub_task = None
