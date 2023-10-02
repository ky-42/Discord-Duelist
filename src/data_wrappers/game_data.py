from dataclasses import asdict, dataclass
from typing import Type, TypeVar

import redis.asyncio as redis

from data_types import GameId
from exceptions import GameNotFound


class GameData:
    """
    API wrapper for reddis db which handles the data for active games

    All data in the db is in form
    GameId: GameData
    """

    __db_number = 0
    __pool = redis.Redis(db=__db_number)

    @dataclass
    class GameDataClass:
        """
        Class must be inherited by all game data classes
        """

        pass

    # GameDataClass is a type hint for a class that inherits from GameDataClass
    GDC = TypeVar("GDC", bound=GameDataClass)

    @staticmethod
    async def retrive_data(game_id: GameId, data_class: Type[GDC]):
        if game_state := await GameData.__pool.json().get(game_id):
            return data_class(**game_state)
        raise GameNotFound(f"Game {game_id} not found")

    @staticmethod
    async def store_data(game_id: GameId, data: Type[GDC]):
        # TODO: add timeout
        await GameData.__pool.json().set(game_id, ".", asdict(data))

    @staticmethod
    async def delete_data(game_id: GameId):
        await GameData.__pool.delete(game_id)
