from datetime import timedelta
from typing import List

import redis.asyncio as redis_sync

from data_types import GameId
from exceptions import GameNotFound


class ConfirmMessages:
    """
    API wrapper for reddis db which handles the status of games

    All data in the db is in form
    GameId: List[MessageId]
    """

    __db_number = 3
    __pool = redis_sync.Redis(db=__db_number)

    @staticmethod
    async def set_messages(
        game_id: GameId, message_ids: List[int], expire_timeout: timedelta
    ):
        for message_id in message_ids:
            await ConfirmMessages.__pool.rpush(game_id, message_id)
        await ConfirmMessages.__pool.expire(game_id, expire_timeout)

    @staticmethod
    async def get_messages(game_id: GameId) -> List[int]:
        a = await ConfirmMessages.__pool.get(game_id)
        if a is not None:
            return [int(message_id) for message_id in a]
        raise GameNotFound(f"Game {game_id} not found")

    @staticmethod
    async def delete_messages(game_id: GameId):
        await ConfirmMessages.__pool.delete(game_id)
