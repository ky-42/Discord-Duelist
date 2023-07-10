import redis.asyncio as redis
from . import GameId
from dataclasses import asdict
from exceptions.game_exceptions import ActiveGameNotFound
from typing import TypeVar, Generic

T = TypeVar('T')


class GameData:
    """
    API wrapper for reddis db which handles the data for active games

    All data in the db is in form
    GameId: GameData
    """

    __db_number = 0
    __pool = redis.Redis(db=__db_number)

    @staticmethod
    async def retrive_data(game_id: GameId, data_class):
        if (game_state := await GameData.__pool.json().get(game_id)):
            return data_class(**game_state)
        raise ActiveGameNotFound
    
    @staticmethod
    async def store_data(game_id: GameId, data):
        # TODO: add timeout
        await GameData.__pool.json().set(game_id, '.', asdict(data))
