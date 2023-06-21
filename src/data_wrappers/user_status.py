import redis
import redis.asyncio as redis_sync
from dataclasses import dataclass, asdict
from typing import List
from . import GameStatus
import discord
from helpers import watch_helper
from typing import Type
from exceptions.general_exceptions import PlayerNotFound

class UserStatus:
    
    """
    API wrapper for reddis db which handles the status of players
    
    All data in the db is in the form
    UserId: UserState
    """

    __db_number = 2
    __pool = redis_sync.Redis(db=__db_number)
    
    UserId = int
    
    @dataclass
    class UserState:
        current_game: str
        queued_games: List[str]

    @staticmethod
    async def get_status(user_id: UserId) -> UserState | None:
        if current_status := await UserStatus.__pool.json().get(user_id):
            return UserStatus.UserState(**current_status)

    @staticmethod
    async def check_in_game(user_id: UserId) -> bool:
        current_status = await UserStatus.get_status(user_id)
        
        if current_status:
            return True
        return False
    
    @staticmethod
    @watch_helper(__pool, "user_id")
    async def join_game(
        user_id: UserId,
        game_id: GameStatus.GameId,
        pipe: redis_sync.client.Pipeline = None # type: ignore
    ):
        if await pipe.json().get(user_id):
            await pipe.json().arrappend(str(user_id), '.queued_games', game_id)
        else:
            await pipe.json().set(user_id, '.', asdict(UserStatus.UserState(
                current_game=game_id,
                queued_games=[]
            )))
    
    @staticmethod
    async def check_if_in_game(user_ids: List[UserId], game_id: GameStatus.GameId):
        while len(user_ids):
            user_id = user_ids.pop()
            if status := await UserStatus.get_status(user_id):
                if status.current_game != game_id:
                    return False
            else:
                raise PlayerNotFound(user_id)
        return True

    @staticmethod
    async def game_finished(user_id: UserId, game_id: GameStatus.GameId):
        pass
    
    @staticmethod
    async def qued_game_canceled(user_id: UserId, game_id: GameStatus.GameId):
        pass