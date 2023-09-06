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
            0 = unconfirmed | 1 = confirmed but queued | 2 = in progress | 3 = finished

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
    __expire_pubsub_task: asyncio.Task | None = None

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
    async def set_game_expire(game_id: GameId, extend_time: timedelta):
        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.expire(shadow_key, extend_time)

    @staticmethod
    async def add_game(state: GameState, timeout: timedelta) -> GameId:
        game_id = GameStatus.__create_game_id()

        await GameStatus.__pool.json().set(game_id, ".", asdict(state))

        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.set(shadow_key, -1)
        await GameStatus.__pool.expire(shadow_key, timeout)

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
    async def delete_game(game_id: GameId):
        await GameStatus.__pool.delete(game_id)

        shadow_key = GameStatus.__get_shadow_key(game_id)
        await GameStatus.__pool.delete(shadow_key)

    @staticmethod
    @pipeline_watch(__pool, "game_id", ActiveGameNotFound)
    async def player_confirm(
        pipe: redis_async_client.Pipeline,
        game_id: GameId,
        player_id: int,
    ) -> List[int]:
        """
        Adds a player to the confirmed list and removes them from the unconfirmed list
        Returns unconfirmed list
        """

        # Make sure player exists
        if (
            index := await pipe.json().arrindex(
                game_id, ".unconfirmed_players", player_id
            )
        ) > -1:
            # Switch to buffered mode after watch
            pipe.multi()
            pipe.json().arrpop(game_id, ".unconfirmed_players", index)
            pipe.json().arrappend(game_id, ".confirmed_players", player_id)
            pipe.json().get(game_id, ".unconfirmed_players")
            results = await pipe.execute()

            return results[2]

        else:
            raise PlayerNotFound(player_id)

    @staticmethod
    async def set_game_queued(game_id: GameId):
        await GameStatus.__pool.json().set(game_id, ".status", 1)

    @staticmethod
    async def set_game_in_progress(game_id: GameId):
        await GameStatus.__pool.json().set(game_id, ".status", 2)

    @staticmethod
    async def expire_handler(msg):
        """

        IMPORTANT: Could cause problems if multiple instances of the server are running
        """
        for callback in GameStatus.__expire_callbacks.values():
            try:
                msg = msg["data"].decode("utf-8")
                if msg.startswith(GameStatus.__get_shadow_key("")):
                    expired_game_data = await GameStatus.get_game(msg.split(":")[1])
                    game_key = msg.split(":")[1]
                else:
                    print("Not shadow key")
                    continue
            except AttributeError:
                raise Exception("Message not in utf-8 format")
            except ActiveGameNotFound:
                raise ActiveGameNotFound("Expired shadow key game id not found")
            except IndexError:
                raise IndexError("Shadow key not in correct format")
            except:
                raise Exception("Unknown error")
            else:
                await callback(game_key, expired_game_data)
                await GameStatus.delete_game(game_key)

    @staticmethod
    async def add_expire_handler(func: Callable[[GameId, GameState], Awaitable[None]]):
        """

        IMPORTANT: Could cause problems if multiple instances of the server are running
        """
        if not GameStatus.__expire_pubsub_task:
            pubsub_obj = GameStatus.__pool.pubsub()
            await GameStatus.__pool.config_set("notify-keyspace-events", "Ex")
            await pubsub_obj.psubscribe(
                **{
                    f"__keyevent@{GameStatus.__db_number}__:expired": GameStatus.expire_handler
                }
            )
            GameStatus.__expire_pubsub_task = asyncio.create_task(pubsub_obj.run())

        if (name := func.__name__) not in GameStatus.__expire_callbacks:
            GameStatus.__expire_callbacks[name] = func
        else:
            raise FuncExists(name)

    @staticmethod
    async def remove_expire_handler(func: Callable[[GameId, GameState], None]):
        """

        IMPORTANT: Could cause problems if multiple instances of the server are running
        """
        if (name := func.__name__) not in GameStatus.__expire_callbacks:
            raise FuncNotFound(name)
        else:
            del GameStatus.__expire_callbacks[name]

            if (
                len(GameStatus.__expire_callbacks.keys()) == 0
                and GameStatus.__expire_pubsub_task
            ):
                await GameStatus.__pool.config_set("notify-keyspace-events", "")
                GameStatus.__expire_pubsub_task.cancel()
                # FIGURE OUT WHY THIS IS NEED IF AT ALL
                # I put it here cause if you hover the pubsub
                # classes run func it shows this in the example
                print(await GameStatus.__expire_pubsub_task)
                print("his")

                GameStatus.__expire_pubsub_task = None
